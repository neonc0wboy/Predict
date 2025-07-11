import os
import mnemonic
import pexpect

words=mnemonic.mnemonic.main
wordstr=""
wordstr=wordstr+str(mnemonic.mnemonic.main())
try:
    with open('example.txt', 'w') as file:
        file.write(wordstr)
except IOError as e:
    print(f"An error occurred: {e}")
