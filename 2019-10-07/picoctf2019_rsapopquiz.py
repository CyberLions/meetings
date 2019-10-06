# Author: Cole Daubenspeck
#
# Written for picoCTF 2019 - rsa-pop-quiz
# Requires Python 3.6 and above
import socket
import time
import json


ADDRESS = '2019shell1.picoctf.com'
PORT = 30962


def receive_line(connection):
    result = ''
    try:
        while True:
            data = connection.recv(1).decode()
            if data == '\n':
                return result
            else:
                result += data
    except BlockingIOError:
        return result


# Taken from https://stackoverflow.com/questions/4798654/modular-multiplicative-inverse-function-in-python
def egcd(a, b):  # The Euclidean algorithm for finding the greatest common divisor given two numbers
    if a == 0:
        return (b, 0, 1)
    else:
        g, y, x = egcd(b % a, a)
        return (g, x - (b // a) * y, y)


# Taken from https://stackoverflow.com/questions/4798654/modular-multiplicative-inverse-function-in-python
def modinv(a, m):
    g, x, y = egcd(a, m)
    if g != 1:
        raise Exception('modular inverse does not exist')
    else:
        return x % m


def gather_information(connection):
    variable_dictionary = {}
    reading_variables = False
    reading_goal = False
    while True:
        content = receive_line(connection)
        print(content)
        # Check if the state changes
        if '#### NEW PROBLEM ####' in content:
            print('>>> beginning to read variables')
            reading_variables = True
            continue
        elif '##### PRODUCE THE FOLLOWING ####' in content:
            print('>>> beginning to read goal')
            reading_variables = False
            reading_goal = True
            continue
        elif 'IS THIS POSSIBLE and FEASIBLE?' in content:
            return variable_dictionary  # End of method
        
        if reading_variables:  # Record value of variable
            broken_content = content.split(':')
            variable_name = broken_content[0].strip()
            variable_value = int(broken_content[1].strip())
            variable_dictionary[variable_name] = variable_value
        elif reading_goal:
            variable_dictionary['goal'] = content
            print('GOAL = ' + content)


def solve_variables(variables):
    # Grab the variables out of dictionary so it's easier to reference
    p = variables.get('p', None)
    q = variables.get('q', None)
    n = variables.get('n', None)
    d = variables.get('d', None)
    e = variables.get('e', None)
    totient = variables.get('totient(n)', None)
    plaintext = variables.get('plaintext', None)
    ciphertext = variables.get('ciphertext', None)

    # Solve patterns
    if not n and p and q:  # Solve for n using p and q
        n = p * q
        variables['n'] = n
        solve_variables(variables)

    elif not q and n and p:  # Solve for q using n and p
        q = n//p
        variables['q'] = q
        solve_variables(variables)

    elif not p and n and q:  # Solve for p using n and q
        p = n//q
        variables['p'] = p
        solve_variables(variables)

    elif not d and e and totient:  # Solve for d given e and the totient (d is the modular inverse of e mod totient)
        d = modinv(e, totient)
        variables['d'] = d
        solve_variables(variables)

    elif not totient and p and q:  # Solve for the totient
        totient = (p-1) * (q-1)
        variables['totient(n)'] = totient
        solve_variables(variables)

    elif not plaintext and ciphertext and n and d:  # Decrypt ciphertext
        plaintext = pow(ciphertext, d, n)
        variables['plaintext'] = plaintext
        solve_variables(variables)

    elif not ciphertext and plaintext and n and e:  # Encrypt plaintext
        ciphertext = pow(plaintext, e, n)
        variables['ciphertext'] = ciphertext
        solve_variables(variables)

    else:
        return


def solve_problem(connection):
    print('>>> Gathering all info about this challenge')
    variables = gather_information(connection)
    print('>>> Gathered variables')
    print(json.dumps(variables, indent=4, sort_keys=True))
    print('>>> Solving variables')
    solve_variables(variables)
    print(json.dumps(variables, indent=4, sort_keys=True))
    print('>>> Is feasible?')
    # Determine if the problem can be solved, and enter the input as appropriate
    goal_solved = variables.get(variables.get('goal'), None)
    if goal_solved:
        print(f"YES: {goal_solved}")
        connection.sendall('Y\n'.encode())
        time.sleep(0.25)
        # Receive prompt where we enter the number
        content = receive_line(connection)
        print(content)
        content = receive_line(connection)
        print(f'{content}{goal_solved}')
        connection.sendall(f'{goal_solved}\n'.encode())
        time.sleep(0.25)
        # Receive success message
        content = receive_line(connection)
        print(content)
    else:
        print("NO, this is unsolvable")
        connection.sendall('N\n'.encode())
        time.sleep(0.25)
        # Receive success message
        content = receive_line(connection)
        print(content)


def main():
    # Setup connection to server
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.connect((ADDRESS, PORT))
    connection.setblocking(False)

    # Solve problems endlessly (needs to be manually stopped if it hits an error or completes)
    while True:
        print('~' * 64)
        solve_problem(connection)
        print('~' * 64)


if __name__ == '__main__':
    main()
