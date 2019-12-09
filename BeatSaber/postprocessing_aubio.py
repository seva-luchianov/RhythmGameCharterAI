import numpy as np
from os import listdir
from os.path import isfile, join, isdir
import cv2
import soundfile as sf
import csv
import pickle as pkl
import random

def main2(directory):

    with open('./output/Normal.dat', 'r') as f:
        line = f.readline()
        choreo = eval(line)
        choreo['_obstacles'] = [] # set the obstacles to empty, since we didnt predict those
        choreo['_notes'] = [] # clear both the notes and events
        choreo['_events'] = []

        files = [join(directory, f) for f in listdir(directory) if isfile(join(directory, f))]
        files.sort()
        samplerate = 44100 # this is static
        for file in files:
            with open(file, 'rb') as f2:
                ## NOTE For reconstruction, this data needs to be added to *items*
                sample = pkl.load(f2)
                #name = sample['name'] # this is needed for reconstruction of the song
                #data = sample['songdata']
                name = sample['name']
                time = sample['time']
                label = sample['label'] # something is off that I gotta fix
                print(name, samplerate)
                argmax = np.unravel_index(label.argmax(), label.shape)
                cutDirection = argmax[3]
                lineLayer = argmax[1]
                lineIndex = argmax[2]
                type = argmax[0]
                note = {'_cutDirection': cutDirection, '_lineIndex': lineIndex, '_lineLayer': lineLayer, '_time': time, '_type': type}
                # we're just going to randomly assign lighting
                event = {'_time': time, '_type': type, '_value': cutDirection}
                choreo['_notes'].append(note)
                choreo['_events'].append(event)

        print(choreo)

    with open('./output/Normal.dat', 'w') as f:
        f.write(repr(choreo).replace('\'', '\"').replace(' ', ''))

    # notes = []
    # for i in range(len(mapping)):
    #     print(i)

    #notes = sample['notes']
    #lights = sample['lights']
    #obstacles = sample['obstacles'] # to be added in the future
    # for time in range(int(songlength)):
    #     window = data[samplerate*time:samplerate*(time+1)]
    #     beatrate = 147
    #     ## Old Code, too high dimensional
    #     # label = np.zeros([beatrate+1, 5, 3, 2, 5])
    #     # for entry in notes:
    #     #     if entry['_time'] >= time and entry['_time'] < time + 1 and entry['_type'] < 3:
    #     #         # bandied fix for the weird omnidirectional boxes (8) - don't want a massive tensor, could set to index 4
    #     #         if (entry['_cutDirection']) > 3:
    #     #             entry['_cutDirection'] = 4
    #     #         #print(np.floor((entry['_time'] % 1) * beatrate).astype(int), ((entry['_time'] % 1) * beatrate))
    #     #         label[np.floor((entry['_time'] % 1) * beatrate).astype(int), entry['_lineIndex'], entry['_lineLayer'], entry['_type'], entry['_cutDirection']] = 1
    #     #         with open('./samples_window/' + file.replace('.pkl','').replace('./samples/','') + str(time) + '.pkl', 'wb') as f2:
    #     #             pkl.dump({'name':name, 'time':entry['_time'], 'window':window, 'label':label}, f2)
    #     label = np.zeros([beatrate+1])
    #     #for entry in notes:
    #     #    if entry['_time'] >= time and entry['_time'] < time + 1 and entry['_type'] < 3:
    #     #        # bandied fix for the weird omnidirectional boxes (8) - don't want a massive tensor, could set to index 4
    #     #        if (entry['_cutDirection']) > 3:
    #     #            entry['_cutDirection'] = 4
    #     #        #print(np.floor((entry['_time'] % 1) * beatrate).astype(int), ((entry['_time'] % 1) * beatrate))
    #     #        label[np.floor((entry['_time'] % 1) * beatrate).astype(int)] = 1
    #     with open('./samples_infer_window/' + file.replace('.pkl','').replace(directory,'') + str(time) + '.pkl', 'wb') as f2:
    #         pkl.dump({'name':name, 'time':time, 'window':window, 'label':label}, f2)
                    

if __name__ == '__main__':
    directory = './output_infer/'
    #main(directory)
    main2(directory) #second preprocessing needed 