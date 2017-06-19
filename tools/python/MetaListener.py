import h5py
import numpy as np
import zmq
import json
import argparse
import os
import logging
import sys

class MetaWriter:

    def __init__(self, directory, logger, acquisitionID):
        self.logger = logger
        self.acquisitionID = acquisitionID
        self.numberProcessorsRunning = 0
        self.frameOffsetDict = {}
        self.frameDataDict = {}
        self.frameAppendixDict = {}
        self.seriesCreated = False
        self.configCreated = False
        self.flatfieldCreated = False
        self.pixelMaskCreated = False
        self.countrateCreated = False
        self.globalAppendixCreated = False
        self.directory = directory
        self.finished = False
        
        self.startNewAcquisition()
        

    def startNewAcquisition(self):
        
        self.currentFrameCount = 0
        self.frameOffsetDict.clear()
        self.frameDataDict.clear()
        self.frameAppendixDict.clear()

        metaFileName = self.acquisitionID + '_meta.hdf5'

        fullFileName = self.directory + '/' + metaFileName

        self.logger.info("Writing meta data to: %s" % fullFileName)

        self.f = h5py.File(fullFileName, "w")

        self.startDset = self.f.create_dataset("start_time", (0,), maxshape=(None,), dtype='int64', fillvalue=-1)
        self.stopDset = self.f.create_dataset("stop_time", (0,), maxshape=(None,), dtype='int64', fillvalue=-1)
        self.realDset = self.f.create_dataset("real_time", (0,), maxshape=(None,), dtype='int64', fillvalue=-1)
        self.frameDset = self.f.create_dataset("frame", (0,), maxshape=(None,), dtype='int64', fillvalue=-1)
        self.sizeDset = self.f.create_dataset("size", (0,), maxshape=(None,), dtype='int64', fillvalue=-1)
        self.hashDset = self.f.create_dataset("hash", (0,), maxshape=(None,), dtype=h5py.special_dtype(vlen=str))
        self.encodingDset = self.f.create_dataset("encoding", (0,), maxshape=(None,), dtype=h5py.special_dtype(vlen=str))
        self.dtypeDset = self.f.create_dataset("datatype", (0,), maxshape=(None,), dtype=h5py.special_dtype(vlen=str))
        self.frameSeriesDset = self.f.create_dataset("frame_series", (0,), maxshape=(None,), dtype='int64', fillvalue=-1)
        self.frameAppendixDset = self.f.create_dataset("frameAppendix", (0,), maxshape=(None,), dtype=h5py.special_dtype(vlen=str))
        self.frameWrittenDset = self.f.create_dataset("frame_written", (0,), maxshape=(None,), dtype='int64', fillvalue=-1)
        self.offsetWrittenDset = self.f.create_dataset("offset_written", (0,), maxshape=(None,), dtype='int64', fillvalue=-1)

        self.seriesCreated = False
        self.configCreated = False
        self.flatfieldCreated = False
        self.pixelMaskCreated = False
        self.countrateCreated = False
        self.globalAppendixCreated = False

        return

    def handleGlobalHeaderNone(self, message):
        self.logger.debug('Handling global header none for acqID ' + self.acquisitionID)
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
        self.logger.debug('Handling global header cfg for acqID ' + self.acquisitionID)
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
        self.logger.debug('Handling flatfield header for acqID ' + self.acquisitionID)
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
        self.logger.debug('Handling mask header for acqID ' + self.acquisitionID)
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
        self.logger.debug('Handling countrate header for acqID ' + self.acquisitionID)
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
        self.logger.debug('Handling global header appendix for acqID ' + self.acquisitionID)

        if self.globalAppendixCreated == True:
	        self.logger.debug('global appendix already created')
	        return

        self.globalAppendixCreated = True

        nps = np.str(appendix)
        appendixDset = self.f.create_dataset("globalAppendix", data=nps)
        appendixDset.flush()
        return

    def handleData(self, header ):
        self.logger.debug('Handling image data for acqID ' + self.acquisitionID)
        self.logger.debug(header)

        frameId = header['frame']

        # Check if we know the offset to write to yet, if so write the frame, if not store the data until we do know.
        if (self.frameOffsetDict.has_key(frameId) == True):
            self.writeFrameData(self.frameOffsetDict[frameId], header)
        else:
            self.frameDataDict[frameId] = header

        return

    def handleImageAppendix(self, header, appendix ):
        self.logger.debug('Handling image appendix for acqID ' + self.acquisitionID)
        self.logger.debug(header)

        frameId = header['frame']

        # Check if we know the offset to write to yet, if so write the appendix, if not store the data until we do know.
        if (self.frameOffsetDict.has_key(frameId) == True):
            self.writeFrameAppendix(self.frameOffsetDict[frameId], appendix)
        else:
            self.frameAppendixDict[frameId] = appendix

        return

    def handleEnd(self, message ):
        self.logger.debug('Handling end for acqID ' + self.acquisitionID)
        
        return

    def handleFrameWriterWriteFrame(self, value ):
        self.logger.debug('Handling frame writer write frame for acqID ' + self.acquisitionID)
        self.logger.debug(value)
        frame_number = value['frame']
        offset_value = value['offset']
        rank = value['rank']
        num_processes = value['proc']
        
        offsetToWriteTo = (offset_value * num_processes) + rank

        self.frameOffsetDict[frame_number] = offsetToWriteTo

        numFrameOffsetsWritten = self.frameWrittenDset.size

        self.frameWrittenDset.resize(numFrameOffsetsWritten+1, axis=0)
        self.frameWrittenDset[numFrameOffsetsWritten] = frame_number

        self.offsetWrittenDset.resize(numFrameOffsetsWritten+1, axis=0)
        self.offsetWrittenDset[numFrameOffsetsWritten] = offsetToWriteTo

        # Check if we have the data and/or appendix for this frame yet. If so, write it in the offset given
        if (self.frameDataDict.has_key(frame_number) == True):
            self.writeFrameData(offsetToWriteTo, self.frameDataDict[frame_number])
            del self.frameDataDict[frame_number]

            if (self.frameAppendixDict.has_key(frame_number) == True):
                self.writeFrameAppendix(offsetToWriteTo, self.frameAppendixDict[frame_number])
                del self.frameAppendixDict[frame_number]

        # So that the dictionary doesn't grow too large, only keep the last 1000 frame/offset values
        if (self.frameOffsetDict.has_key(frame_number-1000)):
            del self.frameOffsetDict[frame_number-1000]

        return

    def handleFrameWriterCreateFile(self, userHeader, fileName ):
        self.logger.debug('Handling frame writer create file for acqID ' + self.acquisitionID)
        self.logger.debug(userHeader)
        self.logger.debug(fileName)

        self.numberProcessorsRunning = self.numberProcessorsRunning + 1

        return

    def handleFrameWriterCloseFile(self):
        self.logger.debug('Handling frame writer close file for acqID ' + self.acquisitionID)

        self.numberProcessorsRunning = self.numberProcessorsRunning - 1

        if self.numberProcessorsRunning == 0:
	        self.logger.info('Last processor ended. Closing file')

	        self.startDset.flush()
	        self.stopDset.flush()
	        self.realDset.flush()
	        self.frameDset.flush()
	        self.sizeDset.flush()
	        self.hashDset.flush()
	        self.encodingDset.flush()
	        self.dtypeDset.flush()
	        self.frameSeriesDset.flush()
	        self.frameAppendixDset.flush()
	        self.frameWrittenDset.flush()
	        self.offsetWrittenDset.flush()
            
	        self.f.close()
	        
	        self.finished = True
        else:
	        self.logger.info('Processor ended, but not the last')

        return

    def writeFrameData(self, offset, header):

        if offset + 1 > self.currentFrameCount:
	        self.currentFrameCount = offset + 1
	        self.startDset.resize(self.currentFrameCount, axis=0)
	        self.stopDset.resize(self.currentFrameCount, axis=0)
	        self.realDset.resize(self.currentFrameCount, axis=0)
	        self.frameDset.resize(self.currentFrameCount, axis=0)
	        self.sizeDset.resize(self.currentFrameCount, axis=0)
	        self.hashDset.resize(self.currentFrameCount, axis=0)
	        self.encodingDset.resize(self.currentFrameCount, axis=0)
	        self.dtypeDset.resize(self.currentFrameCount, axis=0)
	        self.frameSeriesDset.resize(self.currentFrameCount, axis=0)
	        self.frameAppendixDset.resize(self.currentFrameCount, axis=0)

        self.startDset[offset] = header['start_time']
        self.stopDset[offset] = header['stop_time']
        self.realDset[offset] = header['real_time']
        self.frameDset[offset] = header['frame']
        self.sizeDset[offset] = header['size']
        self.hashDset[offset] = header['hash']
        self.encodingDset[offset] = header['encoding']
        self.dtypeDset[offset] = header['type']
        self.frameSeriesDset[offset] = header['series']

        return

    def writeFrameAppendix(self, offset, appendix):
        nps = np.str(appendix)
        self.frameAppendixDset[offset] = nps
        return
    	
class MetaListener:
	
    def __init__(self, directory, inputs):
        self.inputs = inputs
        self.directory = directory
        self.writers = {}
				
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
        message = receiver.recv_json()
        print message
        userheader = message['header']
        print userheader
        
        if 'acqID' in userheader:
          self.logger.info('Had header')
          acquisitionID = userheader['acqID']
        else:
        	self.logger.warn('Didnt have header')
        	acquisitionID = ''
        	
        if acquisitionID in self.writers:
        	self.logger.info('Writer is in writers')
        else:
        	self.logger.info('Writer not in writers, creating new writer for acquisition [' + acquisitionID + ']')
        	self.writers[acquisitionID] = MetaWriter(self.directory, self.logger, acquisitionID)
        	
        writer = self.writers[acquisitionID]

        if message['parameter'] == "eiger-globalnone":
	        receiver.recv_json()
	        writer.handleGlobalHeaderNone(message)
        elif message['parameter'] == "eiger-globalconfig":
	        config = receiver.recv_json()
	        writer.handleGlobalHeaderConfig(userheader, config)
        elif message['parameter'] == "eiger-globalflatfield":
	        flatfield = receiver.recv()
	        writer.handleFlatfieldHeader(userheader, flatfield)
        elif message['parameter'] == "eiger-globalmask":
	        mask = receiver.recv()
	        writer.handleMaskHeader(userheader, mask)
        elif message['parameter'] == "eiger-globalcountrate":
	        countrate = receiver.recv()
	        writer.handleCountrateHeader(userheader, countrate)
        elif message['parameter'] == "eiger-headerappendix":
	        appendix = receiver.recv()
	        writer.handleGlobalHeaderAppendix(appendix)
        elif message['parameter'] == "eiger-imagedata":
	        imageMetaData = receiver.recv_json()
	        writer.handleData(imageMetaData)
        elif message['parameter'] == "eiger-imageappendix":
	        appendix = receiver.recv()
	        writer.handleImageAppendix(userheader, appendix)
        elif message['parameter'] == "eiger-end":
	        receiver.recv()
	        writer.handleEnd(message)
        elif message['parameter'] == "createfile":
	        fileName = receiver.recv()
	        writer.handleFrameWriterCreateFile(userheader, fileName)
        elif message['parameter'] == "closefile":
	        fileName = receiver.recv()
	        writer.handleFrameWriterCloseFile()
	        if (writer.finished == True):
	        	del self.writers[acquisitionID]
        elif message['parameter'] == "writeframe":
	        value = receiver.recv_json()
	        writer.handleFrameWriterWriteFrame(value)
        else:
            print 'unknown parameter: ' + str(message)
            value = receiver.recv()
            print 'value: ' + str(value)
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

    mh = MetaListener(args.directory, args.inputs)

    mh.run()

if __name__ == "__main__":
    main()