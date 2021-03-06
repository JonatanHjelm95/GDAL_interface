from PIL import Image
from osgeo import gdal
import os
from os.path import dirname, abspath
import sys
import subprocess
import argparse
import time

#Author = Jonatan@JMHJX

## Download the whl-file that fits your python version
## pip install path_to_whl_file
# WHL files at https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal

#DefaultNDVLookup={'Byte':255, 'UInt16':65535, 'Int16':-32767, 'UInt32':4294967293, 'Int32':-2147483647, 'Float32':1.175494351E-38, 'Float64':1.7976931348623158E+308}

calc_options = {'1': '--calc="A*1.5"',
            '2': '--calc="A*2"',
            '3': '--calc="A*(A>0)" --NoDataValue=0',
            '4': '--type=UInt16 --calc="A+10000'}

timings = []
success = []
failed = []

def convertToTif(inputfolder, filename):
    newfname = filename.split('.')[0]
    im = Image.open(inputfolder+"/"+filename)
    im.save("converted/"+newfname+".tiff", 'TIFF')

def set_format(fm):
    fm = fm.replace('.','').upper()
    if fm == 'JPG' or fm == 'JPEG':
        return 'jpg'
    if fm == 'TIF' or fm == 'TIFF' or fm == 'GTIFF':
        return 'tif'
    else:
        return 'png'

# Getting all the filenames from the input folder
def get_filenames(folder):
    files = []
    for f in os.listdir(folder):
        if '.tif' in f.lower() or '.jpg' in f.lower() or '.png' in f.lower() or '.jpeg' in f.lower() or '.tiff' in f.lower():
            files.append(f)
    return files

# Setting outputfolder
def set_outputfolder(inputfolder, args):
    if args.output is not None:
        return str(args.output)
    else:
        return inputfolder+'_calculated' 

def calcProgress(length, current):
    progress = current / length * 100
    return round(float(progress),2)

def render_progress(progress):
    bar = '['
    for i in range(100):
        if i < int(progress):
            bar += '='
        else:
            bar += '-'
    return bar+']'

# Calculating remaing time by taking the average iteration timing*the remaining iterations
def calc_timing(length, current):
    try:
        timing = sum(timings)/len(timings)
        start_time = length*timing
        current_time = int((length-current)*timing)
        seconds = current_time % (24 * 3600) 
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60 
        return "| time left:  %02d:%02d" % (minutes, seconds) 
    except:
        return 'estimating time'

def show_progress(length, index, res):
    eta = calc_timing(length, index)
    progress = calcProgress(length, index)
    progressbar = render_progress(progress)+ ' ' +str(progress) + '% ' +str(eta)+'  | '+res+ ' | \t' # <- Padding
    print(progressbar, end="\r")

def finish_progress():
    progressbar = render_progress(100)+ ' 100% '
    print(progressbar)
    print('\n Finished calculation. Files calculated: '+ str(len(success))+', failed: '+str(len(failed)))

def get_python_path():
    paths = sys.path
    for p in paths:
        if 'Python3' in p.split('\\')[len(p.split('\\'))-1]:
            return p.replace('\\','/')+'/python.exe'

def get_parent_path():
    return os.path.dirname(__file__).replace('\\','/')


# Calculation is executed here
def calculate(python_path, infile, outpath, fm, option):
    command = python_path + ' '+get_parent_path()+'/gdalwin64-2.1dev/gdal_calc.py -A converted/'+infile+'.tiff --outfile='+outpath+'/'+infile+'.'+set_format(fm)+ ' '+ calc_options[option]
    sys.stdout = open(os.devnull, 'w')
    os.system(command)
    success.append(infile)
    sys.stdout = sys.__stdout__
    return 'calculated '+str(infile)

def purgeConversionFolder():
    try:
        files = []
        for f in os.listdir('converted'):
            os.remove('converted/'+f)
        os.removedirs('converted')
    except:
        pass

def purgeOutputFolder(output):
    try:
        files = []
        for f in os.listdir(output):
            os.remove(output+'/'+f)
        os.removedirs(output)
    except:
        pass

# Exection
def do_calculation(inputfolder, calculation, fm, args):
    python_path = get_python_path()
    purgeConversionFolder()
    fnames = get_filenames(inputfolder)
    # Getting optional args
    outpath = set_outputfolder(inputfolder, args)
    print('Calculating files to', outpath, 'calculation:', calc_options[str(calculation)])
    # Creating output folder
    os.mkdir('converted')
    try:
        # Creating output folder
        os.mkdir(outpath) 
    except:
        answer = input(outpath + ' already exists. Do you wish to overwrite it? y/n \n')
        if answer == 'y':
            purgeOutputFolder(outpath)
            # Recreating output folder
            os.mkdir(outpath)
        else:
            return 
    ######################################
    ### Executing selected calculation ###
    ######################################
    try:
        for i in range(len(fnames)):
            if i % 10 == 0:
                start_time = time.time()
            outfile = fnames[i]
            convertToTif(inputfolder, fnames[i])
            res = calculate(python_path, fnames[i].split('.')[0], outpath, fm, str(calculation))
            show_progress(length=len(fnames), index=i, res=res)
            if i % 10 == 0:
                timings.append(time.time() - start_time)
        finish_progress()
        purgeConversionFolder()
    except Exception as e:
        print(e)
        pass
    #######################################
    ######## Finished calculation #########
    #######################################

def main():
    parser = argparse.ArgumentParser()
    # Mandatory
    parser.add_argument('-i', '--input', help='input folder path', required=True)
    parser.add_argument('-fm', '--format', help='output file format', required=True)
    parser.add_argument('-c', '--calculation', help='calculation type:  1=A*1.5 | 2=A*2 | 3=A*(A>0) | 4=A+10000 (Thermal normalization)', required=True)
    # Optional
    parser.add_argument('-o', '--output', help='output folder path. Default=[inputfolder]_calculated', required=False)
    # Execute
    args = parser.parse_args()
    do_calculation(inputfolder=args.input, calculation=args.calculation, fm=args.format, args=args)


if __name__ == "__main__":
    main()