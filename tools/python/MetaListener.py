import h5py
import numpy as np
import zmq
import json
import argparse
import os
import logging
import sys

class MetaListener:
	
    def __init__(self, directory, inputs):
        self.numberProcessorsRunning = 0;
        self.frameOffset = 0;
        self.acqusitionStarted = False
        self.dataFileName = 'unknown.hdf5'
        self.directory = directory
        self.inputs = inputs

        # create logger
        self.logger = logging.getLogger('meta_listener')
        self.logger.setLevel(logging.DEBUG)

        # create console handler and set level to debug
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)

        # create formatter
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s - %(message)s')

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        self.logger.addHandler(ch)

    def run(self):
        inputsList = self.inputs.split(',')

        context = zmq.Context()

        receiverList = []    

        # Socket to receive messages on
        for x in inputsList:
            newReceiver = context.socket(zmq.SUB)
            newReceiver.connect(x)
            newReceiver.setsockopt(zmq.SUBSCRIBE, '')
            receiverList.append(newReceiver)

        poller = zmq.Poller()
        for eachReceiver in receiverList:
            poller.register(eachReceiver, zmq.POLLIN)

        self.logger.info('Listening...')

        while True:
            socks = dict(poller.poll())
            for receiver in receiverList:
                if socks.get(receiver) == zmq.POLLIN:
                    self.handleMessage(receiver)

        self.logger.info('Finished listening')

        # Finished
        for receiver in receiverList:
            receiver.close(linger=0)

        context.term()

        return

    def handleMessage(self, receiver):
        print 'handling message'
        #message = receiver.recv_json()
        messageRaw = receiver.recv()

        messageCut = "".join([messageRaw.rsplit("}" , 1)[0] , "}"])
        message = json.loads(messageCut)

        if message['parameter'] == "eiger-globalnone":
	        receiver.recv_json()
	        self.handleGlobalHeaderNone(message)
        elif message['parameter'] == "eiger-globalconfig":
	        config = receiver.recv_json()
	        userheader = message['header']
	        self.handleGlobalHeaderConfig(userheader, config)
        elif message['parameter'] == "eiger-globalflatfield":
	        userheader = message['header']
	        flatfield = receiver.recv()
	        self.handleFlatfieldHeader(userheader, flatfield)
        elif message['parameter'] == "eiger-globalmask":
	        userheader = message['header']
	        mask = receiver.recv()
	        self.handleMaskHeader(userheader, mask)
        elif message['parameter'] == "eiger-globalcountrate":
	        userheader = message['header']
	        countrate = receiver.recv()
	        self.handleCountrateHeader(userheader, countrate)
        elif message['parameter'] == "eiger-headerappendix":
	        appendix = receiver.recv()
	        self.handleGlobalHeaderAppendix(appendix)
        elif message['parameter'] == "eiger-imagedata":
	        imageMetaData = receiver.recv_json()
	        self.handleData(imageMetaData)
        elif message['parameter'] == "eiger-imageappendix":
	        userheader = message['header']
	        appendix = receiver.recv()
	        self.handleImageAppendix(userheader, appendix)
        elif message['parameter'] == "eiger-end":
	        receiver.recv()
	        self.handleEnd(message)
        elif message['parameter'] == "createfile":
	        fileName = receiver.recv()
	        self.handleFrameWriterCreateFile(fileName)
        elif message['parameter'] == "closefile":
	        fileName = receiver.recv()
	        self.handleFrameWriterCloseFile()
        elif message['parameter'] == "framewriter-offset":
	        value = receiver.recv()
	        self.handleFrameWriterOffset(value)
        else:
            print 'unknown parameter: ' + str(message)
            value = receiver.recv()
            print 'value: ' + str(value)
        return

    def startNewAcquisition(self):
        
        self.logger.debug("NumberProcessorsRunning: %d" % self.numberProcessorsRunning)

        if self.acqusitionStarted == False:

            self.currentFrameCount = 0

            self.logger.debug("Data filename: %s" % self.dataFileName)

            base=os.path.basename(self.dataFileName)
            filename = os.path.splitext(base)[0]

            metaFileName = filename + '_meta.hdf5'

            fullFileName = self.directory + '/' + metaFileName

            self.logger.info("Writing meta data to: %s" % fullFileName)

            self.f = h5py.File(fullFileName, "w")

            self.startDset = self.f.create_dataset("start_time", (0,), maxshape=(None,), dtype='int64', fillvalue=-1)
            self.stopDset = self.f.create_dataset("stop_time", (0,), maxshape=(None,), dtype='int64', fillvalue=-1)
            self.realDset = self.f.create_dataset("real_time", (0,), maxshape=(None,), dtype='int64', fillvalue=-1)
            self.frameDset = self.f.create_dataset("frame", (0,), maxshape=(None,), dtype='int64', fillvalue=-1)
            self.hashDset = self.f.create_dataset("hash", (0,), maxshape=(None,), dtype=h5py.special_dtype(vlen=str))
            self.encodingDset = self.f.create_dataset("encoding", (0,), maxshape=(None,), dtype=h5py.special_dtype(vlen=str))
            self.dtypeDset = self.f.create_dataset("datatype", (0,), maxshape=(None,), dtype=h5py.special_dtype(vlen=str))
            self.frameSeriesDset = self.f.create_dataset("frame_series", (0,), maxshape=(None,), dtype='int64', fillvalue=-1)
            self.frameAppendixDset = self.f.create_dataset("frameAppendix", (0,), maxshape=(None,), dtype=h5py.special_dtype(vlen=str))

            self.seriesCreated = False
            self.configCreated = False
            self.flatfieldCreated = False
            self.pixelMaskCreated = False
            self.countrateCreated = False
            self.globalAppendixCreated = False

            self.acqusitionStarted = True

        return

    def handleGlobalHeaderNone(self, message):
        self.logger.debug('Handling global header none')
        self.logger.debug(message)
        if self.seriesCreated == True:
	        self.logger.debug( 'series already created' )
	        return

        npa = np.array(message['series'])
        self.seriesDset = self.f.create_dataset("series", data=npa)
        self.seriesDset.flush()
        self.seriesCreated = True

        return

    def handleGlobalHeaderConfig(self, header, config ):
        self.logger.debug('Handling global header cfg')
        self.logger.debug(header)
        self.logger.debug(config)

        if self.configCreated == True:
            self.logger.debug( 'config already created' )
        else:
            nps = np.str(config)
            cfgDset = self.f.create_dataset("config", data=nps)
            cfgDset.flush()
            self.configCreated = True

        if self.seriesCreated == True:
            self.logger.debug( 'series already created' )
        else:
            npa = np.array(header['series'])
            seriesDset = self.f.create_dataset("series", data=npa)
            seriesDset.flush()
            self.seriesCreated = True

        return

    def handleFlatfieldHeader(self, header, flatfield ):
        self.logger.debug('Handling flatfield header')
        self.logger.debug(header)
        if self.flatfieldCreated == True:
	        self.logger.debug( 'flatfield already created' )
	        return

        self.flatfieldCreated = True
        npa = np.frombuffer(flatfield, dtype=np.float32)
        shape = header['shape']
        flatfieldDset = self.f.create_dataset("flatfield", (shape[1],shape[0]), data=npa)
        flatfieldDset.flush()
        return

    def handleMaskHeader(self, header, mask ):
        self.logger.debug('Handling mask header')
        self.logger.debug(header)
        if self.pixelMaskCreated == True:
	        self.logger.debug('pixel mask already created')
	        return

        self.pixelMaskCreated = True

        npa = np.frombuffer(mask, dtype=np.uint32)
        shape = header['shape']
        maskDset = self.f.create_dataset("mask", (shape[1],shape[0]), data=npa)
        maskDset.flush()
        return

    def handleCountrateHeader(self, header, countrate ):
        self.logger.debug('Handling countrate header')
        self.logger.debug(header)
        if self.countrateCreated == True:
	        self.logger.debug('countrate already created')
	        return

        self.countrateCreated = True

        npa = np.frombuffer(countrate, dtype=np.float32)
        shape = header['shape']
        countrateDset = self.f.create_dataset("countrate", (shape[1],shape[0]), data=npa)
        countrateDset.flush()
        return

    def handleGlobalHeaderAppendix(self, appendix ):
        self.logger.debug('Handling global header appendix')
        if self.globalAppendixCreated == True:
	        self.logger.debug('global appendix already created')
	        return

        self.globalAppendixCreated = True

        nps = np.str(appendix)
        appendixDset = self.f.create_dataset("globalAppendix", data=nps)
        appendixDset.flush()
        return

    def handleData(self, header ):
        self.logger.debug('Handling image data')
        self.logger.debug(header)

        frameId = header['frame']

        if frameId + self.frameOffset + 1 > self.currentFrameCount:
	        self.currentFrameCount = frameId + self.frameOffset + 1
	        self.startDset.resize(self.currentFrameCount, axis=0)
	        self.stopDset.resize(self.currentFrameCount, axis=0)
	        self.realDset.resize(self.currentFrameCount, axis=0)
	        self.frameDset.resize(self.currentFrameCount, axis=0)
	        self.hashDset.resize(self.currentFrameCount, axis=0)
	        self.encodingDset.resize(self.currentFrameCount, axis=0)
	        self.dtypeDset.resize(self.currentFrameCount, axis=0)
	        self.frameSeriesDset.resize(self.currentFrameCount, axis=0)
	        self.frameAppendixDset.resize(self.currentFrameCount, axis=0)

        self.startDset[frameId + self.frameOffset] = header['start_time']
        self.stopDset[frameId + self.frameOffset] = header['stop_time']
        self.realDset[frameId + self.frameOffset] = header['real_time']
        self.frameDset[frameId + self.frameOffset] = header['frame']
        self.hashDset[frameId + self.frameOffset] = header['hash']
        self.encodingDset[frameId + self.frameOffset] = header['encoding']
        self.dtypeDset[frameId + self.frameOffset] = header['type']
        self.frameSeriesDset[frameId + self.frameOffset] = header['series']

        return

    def handleImageAppendix(self, header, appendix ):
        self.logger.debug('Handling image appendix')
        nps = np.str(appendix)

        frameId = header['frame']

        self.frameAppendixDset[frameId + self.frameOffset] = nps

        return

    def handleEnd(self, message ):
        self.logger.debug('Handling end')

        #self.numberProcessorsRunning = self.numberProcessorsRunning - 1

        #if self.numberProcessorsRunning == 0:
	    #    self.logger.info('Last processor ended. Closing file')

	    #    self.acqusitionStarted = False

	    #    self.startDset.flush()
	    #    self.stopDset.flush()
	    # #   self.realDset.flush()
	    #    self.frameDset.flush()
	    #    self.hashDset.flush()
	    #    self.encodingDset.flush()
	    #    self.dtypeDset.flush()
	    #    self.frameSeriesDset.flush()
	    #    self.frameAppendixDset.flush()
        #    
	    #    self.f.close()
        #else:
	    #    self.logger.info('Processor ended, but not the last')

        
        return

    def handleFrameWriterOffset(self, value ):
        self.logger.debug('Handling frame writer offset')
        self.logger.debug(value)

        self.frameOffset = value

        return

    def handleFrameWriterCreateFile(self, fileName ):
        self.logger.debug('Handling frame writer create file')
        self.logger.debug(fileName)

        self.dataFileName = fileName

        if self.acqusitionStarted == False:
	        self.startNewAcquisition()

        self.numberProcessorsRunning = self.numberProcessorsRunning + 1

        return

    def handleFrameWriterCloseFile(self):
        self.logger.debug('Handling frame writer close file')

        self.numberProcessorsRunning = self.numberProcessorsRunning - 1

        if self.numberProcessorsRunning == 0:
	        self.logger.info('Last processor ended. Closing file')

	        self.acqusitionStarted = False

	        self.startDset.flush()
	        self.stopDset.flush()
	        self.realDset.flush()
	        self.frameDset.flush()
	        self.hashDset.flush()
	        self.encodingDset.flush()
	        self.dtypeDset.flush()
	        self.frameSeriesDset.flush()
	        self.frameAppendixDset.flush()
            
	        self.f.close()
        else:
	        self.logger.info('Processor ended, but not the last')

        return


def options():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputs", default="tcp://127.0.0.1:5558", help="Input enpoints - comma separated list")
    parser.add_argument("-d", "--directory", default="/tmp/", help="Directory to write meta data files to")
    args = parser.parse_args()
    return args

def main():
    print ('Starting status listener...')

    args = options()

    inputs = args.inputs

    mh = MetaListener(args.directory, inputs)

    mh.run()

if __name__ == "__main__":
    main()