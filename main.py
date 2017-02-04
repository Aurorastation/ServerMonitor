from ServerMonitor import *

if __name__ == '__main__':
    print("Starting server monitor.")
    test = ServerMonitor.ServerMonitor('config.yml')

    try:
        print("Running!")
        test.run()
    except Exception as e:
        print("Exception caught, stopping: {0}".format(e))

    input("Press Enter to exit.")