import sys
import getopt
from os import path, walk
from datetime import datetime
from pykml import parser
from pexif import JpegFile

_HELP = "gps_tagger.py -<i|images> <image directory> -<h|history> <history kml>"


def main():
    indir, history = "", ""
    try:
        opts, args = getopt.getopt(sys.argv[1:], "i:l:v", ["images", "locations"])
    except getopt.GetoptError:
        print("Exception")
        print _HELP
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print _HELP
        elif opt in ("-i", "--images"):
            indir = arg
            if not path.isdir(indir):
                print "Images location must be a directory"
                sys.exit(2)
        elif opt in ("-l", "--locations"):
            history = arg
            if not history.endswith(".kml"):
                print "Location history must be a kml file"
                sys.exit(2)
            elif not path.isfile(history):
                print "Location history file must exist"
                sys.exit(2)

    print "Tagging images in {} with {}".format(indir, history)
    with open(history) as his:
        tag(indir, parser.parse(his).getroot())


def tag(impath, kml):
    coords = kml.Document.Placemark.getchildren()[1].getchildren()
    print "Found {} coordinates".format(len(coords) / 2)

    idx = 1  # Skip <altitudeMode>
    last_time = datetime.min  # Time of last assigned location

    kml_date_str = "%Y-%m-%dT%H:%M:%SZ"
    exif_date_str = "%Y:%m:%d %H:%M:%S"

    for root, dirs, files in walk(impath):
        for ifile in sorted(files, reverse=True):  # Sort files in order of most recently taken
            if ifile.lower().endswith(".jpg"):
                filepath = path.join(root, ifile)
                image = JpegFile.fromFile(path.join(root, ifile))

                time_taken = image.get_exif().get_primary().ExtendedEXIF.DateTimeDigitized
                time_taken = datetime.strptime(str(time_taken), exif_date_str)

                print "{} taken {}".format(ifile, time_taken)
                for i in range(idx, len(coords), 2):
                    coord_time = datetime.strptime(str(coords[i]), kml_date_str)  # GPS log time
                    # Note: <= as there can be duplicated coordinate time stamps within 1 second
                    if abs(coord_time - time_taken) <= abs(last_time - time_taken):
                        last_time = coord_time  # New coordinate is closer in time
                    else:
                        # Take previous time and coordinates
                        coord_time = datetime.strptime(str(coords[i - 2]), kml_date_str)
                        coord = coords[i - 1].text.split(" ")  # Longitude, Latitude, Altitude
                        image.set_geo(float(coord[1]), float(coord[0]))
                        image.writeFile(filepath)
                        last_time = coord_time
                        idx = i
                        print "Assigning location {} from {} image taken at {}. Delta time {}".format(coord, coord_time,
                                                                                                 time_taken, abs(
                                coord_time - time_taken))
                        break


if __name__ == "__main__":
    main()
