import numpy as np
import numpy.ctypeslib as npct
import ctypes
import os.path
from sys import platform

from lisa.lisa_configuration import config


SST_TAG_LEN = int(config['ODAS']['SST_tag_len'])
MAX_ODAS_SOURCES = int(config['INCOME_STREAM']['n_sources'])
ODAS_RCV_LIB = config['ODAS']['library']

pTag = ctypes.create_string_buffer(SST_TAG_LEN)


##################
## callback_SSL ##
##################
# struct SSL_src_struct {
# double x;
# double y;
# double z;
# double E;
# }; // SSL src 
class SSL_src_struct(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double), ("z", ctypes.c_double), ("E", ctypes.c_double)]

    def __str__(self):
        return "LOC E={}@({},{},{})".format(self.E, self.x, self.y, self.z)


# struct SSL_struct {
# unsigned int timestamp;
# SSL_src_struct src[MAX_ODAS_SOURCES]; // TODO, Max value or variable?
# }; // SSL struct message
class SSL_struct(ctypes.Structure):
    _fields_ = [("timestamp", ctypes.c_uint), ("src", SSL_src_struct * MAX_ODAS_SOURCES)]

    def __str__(self):
        return "SSL_[{}]-{}".format(self.timestamp, str(self.src))


# void callback_SSL(SSL_struct* data);	
callback_SSL_func = ctypes.CFUNCTYPE(
    None,  # return
    ctypes.POINTER(SSL_struct)  # x
)


##################
## callback_SST ##
##################

# struct SST_src_struct {
# unsigned int id;
# char tag[SST_TAG_LEN]; // TODO, VERIFY THIS IS NOT BUGGY, NO IDEA WHAT IS THE MAX LEN!!!
# double x;
# double y;
# double z;
# double activity;
# }; // SST src 
class SST_src_struct(ctypes.Structure):
    # _fields_=[("id",ctypes.c_uint), ("tag", ctypes.c_char_p*(SST_TAG_LEN+1)), ("x",ctypes.c_double),("y",ctypes.c_double),("z",ctypes.c_double), ("activity",ctypes.c_double)]
    _fields_ = [("id", ctypes.c_uint), ("tag", ctypes.c_char * SST_TAG_LEN), ("x", ctypes.c_double),
                ("y", ctypes.c_double), ("z", ctypes.c_double), ("activity", ctypes.c_double)]

    def __str__(self):
        return "TRACK({}) {} Activity={}@({},{},{})".format(self.id,  self.tag, self.activity, self.x, self.y, self.z)



# struct SSL_struct {
# unsigned int timestamp;
# SSL_src_struct src[MAX_ODAS_SOURCES]; // TODO, Max value or variable?
# }; // SSL struct message
class SST_struct(ctypes.Structure):
    _fields_ = [("timestamp", ctypes.c_uint), ("src", SST_src_struct * MAX_ODAS_SOURCES)]

    def __str__(self):
        return "SST_[{}]-{}".format(self.timestamp, str(self.src))


# callback_SST(SST_struct* data);
callback_SST_func = ctypes.CFUNCTYPE(
    None,  # return
    ctypes.POINTER(SST_struct)  # x
)


####################
## callback_SSS_S ##
####################
array_1d_int16 = npct.ndpointer(dtype=np.int16, ndim=1, flags='CONTIGUOUS')


# callback_SSS_S...
callback_SSS_S_func = ctypes.CFUNCTYPE(
    None,  # return
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_short)
)


####################################
## Start the main loop and config ##
####################################
def get_lisa_reciever():
	file_name = os.path.dirname(__file__) + '/' +  ODAS_RCV_LIB

	if (platform == "linux" or platform == "linux2") and not file_name.endswith('.so'):
		#will work only on linux!
		file_name = file_name + ".so"
	print("Open file RCV lib {}".format(file_name))
	lib_lisa_rcv = ctypes.CDLL(file_name)
	lib_lisa_rcv.start_main_loop.restype = ctypes.c_int
	lib_lisa_rcv.start_main_loop.argtypes = [ctypes.c_char_p]  

	# define SSL register and callback args and output
	lib_lisa_rcv.callback_SSL.restype = None  # with  C++ compiler be sure it is declared as extern "C"
	lib_lisa_rcv.callback_SSL.argtypes = [ctypes.POINTER(SSL_struct)]  # [array_1d_double, .c_int]
	lib_lisa_rcv.register_callback_SSL.restype = None
	lib_lisa_rcv.register_callback_SSL.argtypes = [callback_SSL_func]

	# define SST register and callback args and output
	lib_lisa_rcv.callback_SST.restype = None  # with  C++ compiler be sure it is declared as extern "C"
	lib_lisa_rcv.callback_SST.argtypes = [ctypes.POINTER(SST_struct)]  # [array_1d_double, .c_int]
	lib_lisa_rcv.register_callback_SST.restype = None
	lib_lisa_rcv.register_callback_SST.argtypes = [callback_SST_func]
	
	# define SSS register and callback args and output
	lib_lisa_rcv.callback_SSS_S.restype = None  # with  C++ compiler be sure it is declared as extern "C"
	lib_lisa_rcv.callback_SSS_S.argtypes = [ctypes.c_int,
											array_1d_int16]  # ctypes.c_void_p*65536]#* 65536]#[array_1d_double, .c_int]
	lib_lisa_rcv.register_callback_SSS_S.restype = None
	lib_lisa_rcv.register_callback_SSS_S.argtypes = [callback_SSS_S_func]
	
	return lib_lisa_rcv
	

#####################################
## unload the lisa library##
#####################################
def unload_lisa_reciever(lib_lisa_rcv):
	lib_lisa_rcv.dlclose(lib_lisa_rcv._handle)
