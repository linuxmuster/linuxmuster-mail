#!/usr/bin/python3
#
# linuxmuster-mail.py
# thomas@linuxmuster.net
# 20180209
#

import configparser
import datetime
import getopt
import os
import sys
import re

def usage():
    print('Usage: linuxmuster-mail.py [options]')
    print(' [options] may be:')
    print(' -c <file>, --config=<file> : path to ini file with setup values (mandatory with -s)')
    print(' -r,        --reboot        : reboot system after setup')
    print(' -h,        --help          : print this help')

# get cli args
try:
    opts, args = getopt.getopt(sys.argv[1:], "c:hr", ["config=", "help", "reboot"])
except getopt.GetoptError as err:
    # print help information and exit:
    print(err) # will print something like "option -a not recognized"
    usage()
    sys.exit(2)

# default values
reboot = False
config = None

# evaluate options
for o, a in opts:
    if o in ("-r", "--reboot"):
        reboot = True
    elif o in ("-c", "--config"):
        if os.path.isfile(a):
            config = a
        else:
            usage()
            sys.exit()
    elif o in ("-h", "--help"):
        usage()
        sys.exit()
    else:
        assert False, "unhandled option"
if (config == None):
    usage()
    sys.exit()

# certificate
mailkey = '/etc/linuxmuster/ssl/mail.key.pem'
# template dirs
tpldir = '/usr/share/linuxmuster-mail/templates'
dockertpldir = tpldir + '/docker'
# docker
dockerdir = '/srv/docker/linuxmuster-mail/'
dockerimage = 'tvial/docker-mailserver:latest'

## functions start

# print without linefeed
def printr(msg):
    print(msg, end='', flush=True)

# return datetime string
def dtStr():
    return "{:%Y%m%d%H%M%S}".format(datetime.datetime.now())

# return content of text file
def readTextfile(tfile):
    if not os.path.isfile(tfile):
        return False, None
    try:
        infile = open(tfile , 'r')
        content = infile.read()
        infile.close()
        return True, content
    except:
        print('Cannot read ' + tfile + '!')
        return False, None

# write textfile
def writeTextfile(tfile, content, flag):
    try:
        outfile = open(tfile, flag)
        outfile.write(content)
        outfile.close()
        return True
    except:
        print('Failed to write ' + tfile + '!')
        return False

# mailserver setup
def mailSetup():
    # read ini file
    print('### linuxmuster-mail: mailserver setup')
    if not os.path.isfile(mailkey):
        print('Certificate file ' + mailkey + ' is missing!')
        return 1
    else:
        print('Certificate file ' + mailkey + ' found!')
    # permissions
    os.system('chgrp docker ' + mailkey)
    os.system('chmod 640 ' + mailkey)
    try:
        print('Reading setup data ...')
        setup = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
        setup.read(config)
        domainname = setup.get('setup', 'domainname')
        serverip = setup.get('setup', 'serverip')
        firewallip = setup.get('setup', 'firewallip')
        mailip = setup.get('setup', 'mailip')
        binduserpw = setup.get('setup', 'binduserpw')
        basedn = setup.get('setup', 'basedn')
        smtprelay = setup.get('setup', 'smtprelay')
        smtpuser = setup.get('setup', 'smtpuser')
        smtppw = setup.get('setup', 'smtppw')
        smtpauth = smtpuser + ':' + smtppw
        if smtpuser == '' or smtppw == '':
            smtpauth = ''
        else:
            smtpauth = smtpuser + ':' + smtppw
    except:
        return 1
    # create maildata dir
    maildata = dockerdir + '/maildata/' + domainname
    os.system('mkdir -p ' + maildata)
    os.system('chown docker:docker ' + maildata)
    rc = os.system('chmod 770 ' + maildata)
    if rc != 0:
        return 1
    # create docker configuration
    print('Writing docker configuration ...')
    for f in os.listdir(dockertpldir):
        infile = dockertpldir + '/' + f
        # read template
        rc, content = readTextfile(infile)
        if not rc:
            return 1
        # extract oufile path from first line
        firstline = re.findall(r'# .*\n', content)[0]
        outfile = firstline.partition(' ')[2].replace('\n', '')
        # replace placeholders
        content = content.replace('@@serverip@@', serverip)
        content = content.replace('@@basedn@@', basedn)
        content = content.replace('@@binduserpw@@', binduserpw)
        content = content.replace('@@domainname@@', domainname)
        content = content.replace('@@smtprelay@@', smtprelay)
        content = content.replace('@@smtpauth@@', smtpauth)
        # add date string to content
        content = '# modified by linuxmuster-mail at ' + dtStr() + '\n' + content
        # write outfile
        if not writeTextfile(outfile, content, 'w'):
            return 1
        # copy ldap-users.cf to ldap-groups.cf and ldap-aliases.cf
        if f == 'ldap-users.cf':
            outfile = outfile.replace('ldap-users.cf', 'ldap-groups.cf')
            if not writeTextfile(outfile, content, 'w'):
                return 1
            outfile = outfile.replace('ldap-groups.cf', 'ldap-aliases.cf')
            if not writeTextfile(outfile, content, 'w'):
                return 1
    # pull docker image
    rc = os.system('docker pull ' + dockerimage)
    if rc != 0:
        return 1
    # finally enable the service
    rc = os.system('systemctl enable linuxmuster-mail.service')
    if rc != 0:
        return 1
    return 0

## functions end


rc = mailSetup()

if rc == 0:
    print('\nScript finished successfully!')
    if reboot == True:
        print('Rebooting ...')
        os.system('/sbin/reboot')
    else:
        print('Note: You have to reboot the system to make the changes effective.')
else:
    print('\nScript finished with error!')

sys.exit(rc)
