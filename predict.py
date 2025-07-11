import os

def main():
    entropyb=os.urandom(32)
    entropyh=entropyb.hex()
    print(entropyh)

if __name__ == "__main__":
        main()
