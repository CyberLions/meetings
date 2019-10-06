# Author: Cole Daubenspeck
#
# Written for picoCTF 2019 - rsa-pop-quiz
# Requires Python 3.6 and above
#
# References:
# https://simple.wikipedia.org/wiki/RSA_algorithm#A_working_example
#
import socket
import time
import json


ADDRESS = '2019shell1.picoctf.com'
PORT = 30962

# This method returns a single line of text from the server
def receive_line(connection):
    result = ''  # Start with nothing
    try:
        while True:  # Then start reading data until it's told to stop
            data = connection.recv(1).decode()  # Read a single byte of data and then convert it from binary into text
            if data == '\n':  # If the character is a newline, then this method is finished
                return result  # And it returns the line
            else:
                result += data  # Otherwise the character is appended to the result
    except BlockingIOError:  # This occurs when the server doesn't have anymore data
        return result  # Just return the text collected so far


# Taken from https://stackoverflow.com/questions/4798654/modular-multiplicative-inverse-function-in-python
def egcd(a, b):  # The Euclidean algorithm for finding the greatest common divisor given two numbers
    if a == 0:
        return (b, 0, 1)
    else:
        g, y, x = egcd(b % a, a)
        return (g, x - (b // a) * y, y)


# Taken from https://stackoverflow.com/questions/4798654/modular-multiplicative-inverse-function-in-python
def modinv(a, m):  # This function calculates the modular inverse of a mod m
    g, x, y = egcd(a, m)
    if g != 1:
        raise Exception('modular inverse does not exist')
    else:
        return x % m


# This method collects variables and the goal of the next problem
def gather_information(connection):
    variable_dictionary = {}  # Blank dictionary to be filled with the information this method collects
    # Default states
    reading_variables = False
    reading_goal = False
    # Loop until it's told to stop
    while True:
        # Read a line from the server and print it out
        content = receive_line(connection)
        print(content)
        # Check if the line indicates the states should change. If so, change states and jump to the start of the loop
        if '#### NEW PROBLEM ####' in content:
            print('>>> beginning to read variables')
            reading_variables = True
            continue
        elif '##### PRODUCE THE FOLLOWING ####' in content:
            print('>>> beginning to read goal')
            reading_variables = False
            reading_goal = True
            continue
        elif 'IS THIS POSSIBLE and FEASIBLE?' in content:  # This is the end of the question's prompt
            return variable_dictionary  # Return the information we collected

        # Depending on state, read the information into the dictionary
        if reading_variables:  # If it's reading a given variable's value
            broken_content = content.split(':')  # Split at the colon
            variable_name = broken_content[0].strip()
            variable_value = int(broken_content[1].strip())
            variable_dictionary[variable_name] = variable_value  # And add it to the dictionary
        elif reading_goal:  # If it's reading the goal of the problem
            variable_dictionary['goal'] = content  # Then add the goal into the dictionary
            print('GOAL = ' + content)


# This method takes in the currently-known variables, and derives all other possible variables
def solve_variables(variables):
    # Grab the variables out of dictionary so it's easier to reference
    p = variables.get('p', None)  # Grab the value of 'p', but set the value to None if it doesn't exist
    q = variables.get('q', None)
    n = variables.get('n', None)
    d = variables.get('d', None)
    e = variables.get('e', None)
    totient = variables.get('totient(n)', None)
    plaintext = variables.get('plaintext', None)
    ciphertext = variables.get('ciphertext', None)

    # Solve patterns
    if not n and p and q:  # Solve for n using p and q
        n = p * q  # Solve variable
        variables['n'] = n  # Add it to the dictionary of solved variables
        solve_variables(variables)  # Then recursively call this method to see if any other variables can now be solved

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


# This is the core loop of the program
def solve_problem(connection):
    print('>>> Gathering all info about this challenge')
    variables = gather_information(connection)  # Grab the prompt and all varaibles
    print('>>> Gathered variables')
    print(json.dumps(variables, indent=4, sort_keys=True))
    print('>>> Solving variables')
    solve_variables(variables)  # Figure out what can be solved
    print(json.dumps(variables, indent=4, sort_keys=True))
    print('>>> Is feasible?')
    # Determine if the problem can be solved, and enter the input as appropriate
    goal_solved = variables.get(variables.get('goal'), None)  # See if the goal has a value in the variable list
    if goal_solved:  # If so, it can be solved
        print(f"YES: {goal_solved}")
        connection.sendall('Y\n'.encode())
        time.sleep(0.25)  # Wait for a bit to make sure the server processes our message
        # Receive prompt where we enter the number
        content = receive_line(connection)
        print(content)
        content = receive_line(connection)
        print(f'{content}{goal_solved}')
        # Send the answer to the server
        connection.sendall(f'{goal_solved}\n'.encode())
        time.sleep(0.25)  # Wait for a bit to make sure the server processes our message
        # Receive success message
        content = receive_line(connection)
        print(content)
    else:  # If the goal doesn't exist in the list, then it's unsolvable
        print("NO, this is unsolvable")
        connection.sendall('N\n'.encode())  # Send the appropriate response telling the server it's unsolvable
        time.sleep(0.25)  # Wait for a bit to make sure the server processes our message
        # Receive success message
        content = receive_line(connection)
        print(content)


# This method handles execution of the program
def main():
    # Setup connection to server
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # IPv4 connection that streams data
    connection.connect((ADDRESS, PORT))  # Connect to the server
    connection.setblocking(False)  # Set non-blocking so it doesn't hang if the server isn't sending data

    # Solve problems endlessly (needs to be manually stopped if it hits an error or completes)
    while True:
        print('~' * 64)
        solve_problem(connection)
        print('~' * 64)


# If the code is being run directly (not referenced by another script), run the main method
if __name__ == '__main__':
    main()
