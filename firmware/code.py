#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
# ******************************************************************************
#
#      ██╗     ███████╗███████╗████████╗ █████╗ ██╗
#      ██║     ██╔════╝██╔════╝╚══██╔══╝██╔══██╗██║
#      ██║     █████╗  █████╗     ██║   ███████║██║
#      ██║     ██╔══╝  ██╔══╝     ██║   ██╔══██║██║
#      ███████╗███████╗███████╗   ██║   ██║  ██║██║
#      ╚══════╝╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝
#
# Description: 
# Loader file that loads the program specified in ==> config/mode.py <==
# 
# This code is open source under MIT License.
# (attribution is optional, but always appreciated - Johan von Konow ;)
# ******************************************************************************
import config.config as config # type: ignore
import src.core.boss     
import src.core.pitch
import src.core.pattern
import src.core.chords
import src.core.arp     

def main():
    eval("src.core." + config.MODE + ".main()")               # load mode selected in config.py

if __name__ == "__main__":
    main()