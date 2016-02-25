#!/usr/bin/env python
""" get_transtat_data.py 

A quick little script to connect to RITA's ontime airline
data and pull POST requests to collect airflight performance
stats.
"""
import datetime
from os import rename
from os.path import splitext
from calendar import month_name
from httplib import HTTPConnection
from time import clock
from urllib import urlretrieve
from zipfile import ZipFile
from argparse import ArgumentParser



from post import POST

HOSTNAME = "www.transtats.bts.gov"
TRANSTAT_URL = "http://{host}/DownLoad_Table.asp?" + \
               "Table_ID=236&Has_Group=3&Is_Zipped=0"
FREQUENCY = 1

# the available data set is generally about 3 months behind, make
# sure that we never ask for data that is within the last 3 months
MAX_DATE = datetime.date.today() + datetime.timedelta(days=-90)



def main(opts):
    """

    """

    years = opts.years
    months = opts.months

    # create range of dates
    if len(years) == 2: years = [year for year in xrange(years[0], years[1]+1)]
    if len(months) == 2: months = [month for month in xrange(months[0], months[1]+1)]

    max_year = int(MAX_DATE.strftime('%Y'))
    max_month = int(MAX_DATE.strftime('%m'))

    list_of_files = []

    for year in years:
        # skip all years greater than this year
        if year > max_year: continue
        for month in months:
            # skip all years outside of range
            if year == max_year and month > max_month+1:
                continue
            print "Collecting RITA for: {}/{}".format(month, year)

            list_of_files.append(get_data(month, year))

    if opts.concat is None:
        print "Done"
        return None

    # since we did specify to concat the files, we do that here
    write_header = True
    with open(opts.concat, 'w') as target:
        for csv_file in list_of_files:
            with open(csv_file, 'r') as source:
                lines = source.readlines()
                if not write_header:
                    lines = lines[1:]
                else:
                    write_header = False
                lines = [line for line in lines if line.strip() != '']
                target.writelines(lines)

    print "File {} written".format(opts.concat)

def get_data(month, year, post=POST, host=HOSTNAME,
             url=TRANSTAT_URL, frequency=FREQUENCY):
    """ get_data
        from month and year, create the POST
        and download the RITA data zip package
    """

    # setup the POST
    post = post.format(year=year, month_num=month, month=month_name[month], frequency=frequency)
    # make sure post has no EOLs
    post = post.replace('\n','')

    # create the user agent string, and emulate a browser
    user_agent_string = {
        "Content-Type" : "application/x-www-form-urlencoded",
        }
    
    # make a friendly name for the output file
    output_file = '{0}-{1}'.format(str(month).zfill(2), year)
    zip_file_name = '{}.zip'.format(output_file)
    csv_file_name = '{}.csv'.format(output_file)

    # now collect data
    print "Collecting RITA data for {0},{1}".format(month_name[month], year)

    # lets get some data, create the request string
    request = HTTPConnection(host)

    # set up the url
    url = url.format(host=host)
    print "Sending POST to {}".format(host)

    # keep track of the time, see how long it takes
    tic = clock()
    request.request("POST", url, post, user_agent_string)

    print "get the response from the POST"
    response = request.getresponse()

    if not response.status == 302:
        raise Exception("Request was not successful with response {}".format(
            response.status
            ))

    # get location from headers
    remote_file = response.getheader('location')

    local_file = urlretrieve(remote_file, zip_file_name)

    print "Downloaded: {} in {} seconds".format(zip_file_name, clock()-tic)

    # now unzip the file
    print "Unzipping {}".format(zip_file_name)
    z = ZipFile(zip_file_name)

    # extract the csv file from the zip
    for zip_file in z.namelist():
        if splitext(zip_file)[-1] != '.csv': continue
        z.extract(zip_file)
        rename(zip_file, csv_file_name)
        print "RITA file is: {}".format(csv_file_name)
        break

    # Done, now return the CSV file name
    print "Collected {}".format(csv_file_name)
    return csv_file_name
    

def usage():
    parser = ArgumentParser(description=__doc__)

    parser.add_argument(dest='years',
                        metavar='YEAR[,YEAR]',
                        type=parse_date_range,
                        help='Year(s) for collecting the RITA data')
    parser.add_argument('-m', '--months', dest='months', default="1,12", required=False,
                        metavar="MONTH_START[,MONTH_END]",
                        type=parse_date_range,
                        help="Month")
    parser.add_argument('-c', '--concat', default=None,
                        metavar='FILE_NAME',
                        help="Concat data into single file with specified name,"
                             "without this option, the month-year.csv files are left as is."
    )

    opts = parser.parse_args()
    return opts

def parse_date_range(args):
    """ convert the string into integers """
    return [int(a) for a in args.split(',')]


if __name__ == "__main__":
    opts = usage()
    main(opts)
