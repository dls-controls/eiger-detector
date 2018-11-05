#include <zmq/zmq.hpp>
#include <stdlib.h>
#include <iostream>
#include <sstream>
#include <fstream>

void my_free (void *data, void *hint)
{
    //  We've allocated the buffer using malloc and
    //  at this point we deallocate it using free.
    free (data);
}

void SendFileMessage(zmq::socket_t &socket, std::string filePath, bool more) {

	std::streampos size;
	char * memblock;

	std::ifstream file (filePath.c_str(), std::ios::in|std::ios::binary|std::ios::ate);
	if (file.is_open())
	{
		size = file.tellg();
		memblock = (char*)malloc(sizeof(char) * size); // no need to free this. free is called by 'my_free' arg to message
		file.seekg (0, std::ios::beg);
		file.read (memblock, size);
		file.close();

		zmq::message_t message(memblock, size, my_free);
		memcpy (message.data (), memblock, size);

		if (more) {
			socket.send(message, ZMQ_SNDMORE);
		} else {
			socket.send(message);
		}
	}
	else {
		std::cout << "Unable to open file " << filePath << std::endl;
	}
}

/**
 * Sends ZMQ stream messages that have been stored in a file.
 * To use, edit this file to include all of the files to be sent,
 * setting the 'more' argument to false when that message is the
 * last message in a multipart message.
 *
 */
int main (int argc, char *argv[]) {

	std::string bindAddress("tcp://*:9999");

	std::cout << "Binding to " << bindAddress << "..." << std::endl;

	zmq::context_t context(1);

	// Setup socket to send messages on
	zmq::socket_t socket(context, ZMQ_PUSH);
	socket.bind(bindAddress.c_str());

	long messageIndex = 1;

	std::cout << "Sending messages..." << std::endl;

	// Example use for system test data. Replace with the path to actual files.
	SendFileMessage(socket, "streamfile_1", true);  // Global Header
	SendFileMessage(socket, "streamfile_2", true);  // Global Header Config.
	SendFileMessage(socket, "streamfile_3", true);  // Flatfield Header
	SendFileMessage(socket, "streamfile_4", true);  // Flatfield data blob
	SendFileMessage(socket, "streamfile_5", true);  // Pixelmask header
	SendFileMessage(socket, "streamfile_6", true);  // Pixelmask data blob
	SendFileMessage(socket, "streamfile_7", true);  // Countrate header
	SendFileMessage(socket, "streamfile_8", true);  // Countrate data blob
	SendFileMessage(socket, "streamfile_9", false); // Global Header Appendix. 'more' set to false as is the last message in a multipart message

	SendFileMessage(socket, "streamfile_10", true);  // Image data header
	SendFileMessage(socket, "streamfile_11", true);  // Image data dimensions
	SendFileMessage(socket, "streamfile_12", true);  // Image data blob
	SendFileMessage(socket, "streamfile_13", false); // Image data times.

	SendFileMessage(socket, "streamfile_14", true);  // Image data header
	SendFileMessage(socket, "streamfile_15", true);  // Image data dimensions
	SendFileMessage(socket, "streamfile_16", true);  // Image data blob
	SendFileMessage(socket, "streamfile_17", false); // Image data times.

	SendFileMessage(socket, "streamfile_18", true);  // Image data header
	SendFileMessage(socket, "streamfile_19", true);  // Image data dimensions
	SendFileMessage(socket, "streamfile_20", true);  // Image data blob
	SendFileMessage(socket, "streamfile_21", false); // Image data times.

	SendFileMessage(socket, "streamfile_22", false); // End message

	std::cout << "Finished Sending messages" << std::endl;

	sleep (1);              //  Give 0MQ time to deliver

	return 0;
}