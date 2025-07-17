# axon_bbs/core/services/socket_utils.py
import socket

# Save a reference to the original, standard socket object before it's
# potentially patched by a library like PySocks.
original_socket_socket = socket.socket

