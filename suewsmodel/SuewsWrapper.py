"""
 SUEWS WRAPPER

This python file is the main file for the SUEWS model.

author: Fredrik Lindberg, fredrikl@gvc.gu.se

"""

#import Suews_wrapper_v2015a
#import Suews_wrapper_v2016a
# import Suews_wrapper_v2016b
import Suews_wrapper_v2017b
import os
#import FileDialog

working_path = os.getcwd()

#Suews_wrapper_v2015a.wrapper(working_path)
#Suews_wrapper_v2016a.wrapper(working_path)
Suews_wrapper_v2017b.wrapper(working_path)