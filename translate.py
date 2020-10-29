from PIL import Image, TiffImagePlugin, TiffTags
from osgeo import gdal
import osgeo.osr as osr
import glob
import os
import subprocess
import argparse
import time

#Author = Jonatan@JMHJX

## Download the whl-file that fits your python version
## pip install path_to_whl_file
# WHL files at https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal

timings = []
success = []
failed = []


# Converts GTIFF to TIF
def no_compression(path, filename):
    newfname = filename.split('.')[0]
    im = Image.open(path+"/"+filename)
    TiffImagePlugin.WRITE_LIBTIFF = True
    TiffTags.LIBTIFF_CORE.add(317)
    im.save(path+"/"+newfname+"_cnv.tif")
    os.remove(path.replace('\\','/')+'/'+filename)
    os.rename(path.replace('\\','/')+'/'+newfname+'_cnv.tif', path+'/'+newfname+'.tif')
    TiffImagePlugin.WRITE_LIBTIFF = False
    return newfname+".tif"

# Compresses and replaces all files
def convertToTif_replace(path, filename):
    newfname = filename.split('.')[0]
    im = Image.open(path+"/"+filename)
    TiffImagePlugin.WRITE_LIBTIFF = True
    TiffTags.LIBTIFF_CORE.add(317)
    im.save(path+"/"+newfname+"_cnv.tif", compression = "tiff_lzw")
    # Removes uncompressed image
    os.remove(path.replace('\\','/')+'/'+filename)
    # Renames compressed image to original
    os.rename(path.replace('\\','/')+'/'+newfname+'_cnv.tif', path+'/'+filename)
    TiffImagePlugin.WRITE_LIBTIFF = False
    return newfname+".tif"

# Compresses files and replaces if size is smaller
def convertToTif_replace_largestFile(path, filename):
    newfname = filename.split('.')[0]
    im = Image.open(path+"/"+filename)
    TiffImagePlugin.WRITE_LIBTIFF = True
    TiffTags.LIBTIFF_CORE.add(317)
    im.save(path+"/"+newfname+"_cnv.tif", compression = "tiff_lzw")
    original = os.path.getsize(path.replace('\\','/')+"/"+filename)
    converted = os.path.getsize(path.replace('\\','/')+'/'+newfname+"_cnv.tif")
    if original > converted:
        # Removes uncompressed image
        os.remove(path.replace('\\','/')+'/'+filename)
        # Renames compressed image to original
        os.rename(path.replace('\\','/')+'/'+newfname+'_cnv.tif', path+'/'+filename)
    else:
        os.remove(path.replace('\\','/')+'/'+newfname+'_cnv.tif')
    TiffImagePlugin.WRITE_LIBTIFF = False
    return newfname+".tif"

def set_format(outfile):
    fm = str(outfile.replace('.','').upper())
    if fm == 'JPG':
        return 'JPEG'
    if fm == 'PNG':
        return 'PNG'
    if fm == 'TIFF' or fm == 'TIF' or fm == 'GTIFF':
        return 'GTIFF'
    else:
        return 'GTIFF'



def generate_world_file(path, outfile, xform):
    edit1=xform[0]+xform[1]/2
    edit2=xform[3]+xform[5]/2
    tfw = open(path+'/'+outfile.split('.')[0] + '.tfw', 'wt')
    tfw.write("%0.8f\n" % xform[1])
    tfw.write("%0.8f\n" % xform[2])
    tfw.write("%0.8f\n" % xform[4])
    tfw.write("%0.8f\n" % xform[5])
    tfw.write("%0.8f\n" % edit1)
    tfw.write("%0.8f\n" % edit2)
    tfw.close()

# Getting all the filenames from the input folder
def get_filenames(folder):
    files = []
    for f in os.listdir(folder):
        if '.tif' in f.lower() or '.jpg' in f.lower() or '.png' in f.lower() or '.jpeg' in f.lower() or '.tiff' in f.lower():
            files.append(f)
    return files

# Setting rgb option
def set_rgb_option(args):
    if args.expand is not None:
        if args.expand == 'gray':
            return 'gray'
        if args.expand == 'rgba':
            return 'rgba'
        if args.expand == 'rgb':
            return 'rgb'
        else:
            return 'rgb'
    else:
        return 'rgb' 

# Setting outputfolder
def set_outputfolder(inputfolder, args):
    if args.output is not None:
        return str(args.output)
    else:
        return inputfolder+'_translated' 

# Accepts jpg, png and tif
# bands = [1,2,3]/[1,1,2,3]
def translate_band(infile, path, outfile, bands, fm, tfw, compression):
    try:
        ds = gdal.Open(infile)
        ds = gdal.Translate(path+'/'+outfile, ds, format=set_format(fm), bandList = bands)
        if tfw:
            xform = ds.GetGeoTransform()
            generate_world_file(path, outfile, xform)
        ds = None
        if set_format(fm) == 'GTIFF' and compression == '1':
            convertToTif_replace_largestFile(path,outfile)
        if set_format(fm) == 'GTIFF' and compression == '2':
            convertToTif_replace(path,outfile)
        if set_format(fm) == 'GTIFF' and compression == '3':
            no_compression(path,outfile)
        success.append(infile)        
        return 'Translated '+str(infile)
    except Exception as e:
        fail = {}
        fail[infile] = str(e)
        failed.append(fail)
        return 'Error: '+str(e)
        pass

# Accepts jpg, png and tif
# expand = rgb/rgba/gray
def translate_nodata(infile, path, outfile, fm, tfw):
    try:
        ds = gdal.Open(infile)
        ds = gdal.Translate(path+'/'+outfile, ds, format=set_format(fm), noData=1)
        if tfw:
            xform = ds.GetGeoTransform()
            generate_world_file(path, outfile, xform)
        ds = None
        success.append(infile)        
        return 'Translated '+str(infile)
    except Exception as e:
        fail = {}
        fail[infile] = str(e)
        failed.append(fail)
        return 'Error: '+str(e)
        pass

# Accepts jpg, png and tif
# Resize pixel
# expand = rgb/rgba/gray
def translate_size_px(infile, path, outfile, w, h, fm, tfw):
    try:
        ds = gdal.Open(infile)
        ds = gdal.Translate(path+'/'+outfile, ds, format=set_format(fm), width = w, height=h)
        if tfw:
            xform = ds.GetGeoTransform()
            generate_world_file(path, outfile, xform)
        ds = None
        success.append(infile)        
        return 'Translated '+str(infile)
    except Exception as e:
        fail = {}
        fail[infile] = str(e)
        failed.append(fail)
        return 'Error: '+str(e)
        pass

# Accepts jpg, png and tif
# Resize pct
# expand = rgb/rgba/gray
def translate_size_pct(infile, path, outfile, w, h, fm, tfw):
    try:
        ds = gdal.Open(infile)
        ds = gdal.Translate(path+'/'+outfile, ds, format=set_format(fm), widthPct = w, heightPct=h)
        # Creates TFW File
        if tfw:
            xform = ds.GetGeoTransform()
            generate_world_file(path, outfile, xform)
        ds = None
        success.append(infile)        
        return 'Translated '+str(infile)
    except Exception as e:
        fail = {}
        fail[infile] = str(e)
        failed.append(fail)
        return 'Error: '+str(e)
        pass

# Accepts .gif files
# expand = rgb/rgba/gray
# NOT WORKING ATM
def translate_rgb(infile, path, outfile, expand, fm, tfw):
    ds = gdal.Open(infile)
    ds = gdal.Translate(path+'/'+outfile, ds, format=set_format(fm), rgbExpand = expand)
    if tfw:
        xform = ds.GetGeoTransform()
        generate_world_file(path, outfile, xform)
    ds = None

# Accepts .tif files
# src = [0,0,1,1]
# NOT WORKING ATM
def translate_src(infile, path, outfile, src, fm, tfw):
    ds = gdal.Open(infile)
    ds = gdal.Translate(path+'/'+outfile, ds, format=set_format(fm), srcWin = src)
    if tfw:
        xform = ds.GetGeoTransform()
        generate_world_file(path, outfile, xform)
    ds = None

def set_bands(program):
    bands = []
    # Setting the bands
    b = program.split('b=')[1]
    bs = b.split(',')
    for band in bs:
        bands.append(int(band))
    return bands

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

def show_progress(length, index, res):
    eta = calc_timing(length, index)
    progress = calcProgress(length, index)
    progressbar = render_progress(progress)+ ' ' +str(progress) + '% ' +str(eta)+'  | '+res+ ' | \t' # <- Padding
    print(progressbar, end="\r")

def finish_progress():
    progressbar = render_progress(100)+ ' 100% '
    print(progressbar)
    print('\n Finished translation. Files translated: '+ str(len(success))+', failed: '+str(len(failed)))

def purgeOutputFolder(output):
    try:
        files = []
        for f in os.listdir(output):
            os.remove(output+'/'+f)
        os.removedirs(output)
    except:
        pass

def setCompressionType(compression):
    if compression == None or not str(compression) == '1' and not str(compression) == '2' and not str(compression) == '3':
        return '1'
    else:
        return str(compression)
    

# Exection
def do_translate(inputfolder, program, fm, args):
    fnames = get_filenames(inputfolder)
    # Getting optional args
    expand = set_rgb_option(args)
    output = set_outputfolder(inputfolder, args)
    # Creates tfw file if True
    tfw = True
    # Check if outputfolder already exist
    print('Translating files to', output, 'program:', program, 'format:', fm, 'rgbExpand:',expand)
    try:
        # Creating output folder
        os.mkdir(output) 
    except:
        answer = input(output + ' already exists. Do you wish to overwrite it? y/n \n')
        if answer == 'y':
            purgeOutputFolder(output)
            # Recreating output folder
            os.mkdir(output)
        else:
            return
    ##################################
    ### Executing selected program ###
    ##################################
    try:
        if 'b=' in program:
            bands = set_bands(program)
            compression = input('Which compression type do you wish to use? \n1 = Keeps compressed file if size is smaller than original (Recommended/Default)\n2 = Compresses all files\n3 = No compression (keeps raw images)\n')
            compression = setCompressionType(compression)
            print("You've selected option "+str(compression))
            for i in range(len(fnames)):
                if i % 10 == 0:
                    start_time = time.time()
                outfile = fnames[i].split('.')[0]+'.'+fm
                res = translate_band(inputfolder+'/'+fnames[i], output, outfile, bands, fm, tfw, compression)
                show_progress(length=len(fnames), index=i, res=res)
                if i % 10 == 0:
                    timings.append(time.time() - start_time)
            finish_progress()
        elif 'n' in program:
            for i in range(len(fnames)):
                if i % 10 == 0:
                    start_time = time.time()
                outfile = fnames[i].split('.')[0]+'.'+fm
                res = translate_nodata(inputfolder+'/'+fnames[i], output, outfile, fm, tfw)
                show_progress(length=len(fnames), index=i, res=res)
                if i % 10 == 0:
                    timings.append(time.time() - start_time)
            finish_progress()
        elif 'rpx=' in program:
            dimensions = program.split('rpx=')[1]
            width = int(dimensions.split(',')[0])
            height = int(dimensions.split(',')[1])
            for i in range(len(fnames)):
                if i % 10 == 0:
                    start_time = time.time()
                outfile = fnames[i].split('.')[0]+'.'+fm
                res = translate_size_px(inputfolder+'/'+fnames[i], output, outfile, width, height, fm, tfw)
                show_progress(length=len(fnames), index=i, res=res)
                if i % 10 == 0:
                    timings.append(time.time() - start_time)
            finish_progress()
        elif 'rpc=' in program:
            dimensions = program.split('rpc=')[1]
            width = int(dimensions.split(',')[0])
            height = int(dimensions.split(',')[1])
            for i in range(len(fnames)):
                if i % 10 == 0:
                    start_time = time.time()
                outfile = fnames[i].split('.')[0]+'.'+fm
                res = translate_size_pct(inputfolder+'/'+fnames[i], output, outfile, width, height, fm, tfw)
                show_progress(length=len(fnames), index=i, res=res)
                if i % 10 == 0:
                    timings.append(time.time() - start_time)
            finish_progress()
        else:
            pass
    except Exception as e:
        print(e)
        pass
    ##################################
    ###### Finished Translation ######
    ##################################

def main():
    parser = argparse.ArgumentParser()
    # Mandatory
    parser.add_argument('-i', '--input', help='input folder path', required=True)
    parser.add_argument('-fm', '--format', help='output file format', required=True)
    parser.add_argument('-t', '--translation', help='translation type:  n=noData e.g. n | b=bands e.g. b=1,2,3,4 or b=1,2,3 | rpx=resize (pixels), width height e.g. rpx=50,50 | rpc=resize (percent), width height e.g. rpc=50,50 |', required=True)
    # Optionals
    parser.add_argument('-o', '--output', help='output folder path. Default=[inputfolder]_translated', required=False)
    parser.add_argument('-e', '--expand', help='RGB Expand type(rgb, rgba or gray). Default=rgb', required=False)

    # Execute
    args = parser.parse_args()
    do_translate(inputfolder=args.input, program=args.translation, fm=str(args.format).replace('.',''), args=args)



if __name__ == "__main__":
    main()