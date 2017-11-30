#!/usr/bin/python3
#
# linuxmuster-mail.py
# thomas@linuxmuster.net
# 20171122
#

import configparser
import datetime
import getopt
import netifaces
import os
import sys
import re
from IPy import IP

def usage():
    print('Usage: linuxmuster-mail.py [options]')
    print(' [options] may be:')
    print(' -c <file>, --config=<file> : path to ini file with setup values (mandatory with -s)')
    print(' -n,        --network       : network setup (not with -s)')
    print(' -r,        --reboot        : reboot system after setup')
    print(' -s,        --setup         : start mailserver setup (needs -c)')
    print(' -h,        --help          : print this help')

# get cli args
try:
    opts, args = getopt.getopt(sys.argv[1:], "c:hnrs", ["config=", "help", "network", "reboot", "setup"])
except getopt.GetoptError as err:
    # print help information and exit:
    print(err) # will print something like "option -a not recognized"
    usage()
    sys.exit(2)

# default values
reboot = False
setup = False
network = False
config = None

# evaluate options
for o, a in opts:
    if o in ("-s", "--setup"):
        setup = True
    elif o in ("-n", "--network"):
        network = True
    elif o in ("-r", "--reboot"):
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
if (setup == True and network == True):
    usage()
    sys.exit()
elif (setup == True and config == None):
    usage()
    sys.exit()
elif (setup == False and network == False):
    usage()
    sys.exit()

# hostname
hostname = 'mail'
# certificate
mailkey = '/etc/linuxmuster/ssl/mail.key.pem'
# template dirs
tpldir = '/usr/share/linuxmuster-mail/templates'
dockertpldir = tpldir + '/docker'
networktpldir = tpldir + '/network'
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

# return detected network interfaces
def detectedInterfaces():
    iface_list = netifaces.interfaces()
    iface_list.remove('lo')
    iface_count = len(iface_list)
    if iface_count == 1:
        iface_default = iface_list[0]
    else:
        iface_default = ''
    return iface_list, iface_default

# return default network interface
def getDefaultIface():
    # first try to get a single interface
    iface_list, iface_default = detectedInterfaces()
    if iface_default != '':
        return iface_list, iface_default
    # second if more than one get it by default route
    route = "/proc/net/route"
    with open(route) as f:
        for line in f.readlines():
            try:
                iface, dest, _, flags, _, _, _, _, _, _, _, =  line.strip().split()
                if dest != '00000000' or not int(flags, 16) & 2:
                    continue
                return iface_list, iface
            except:
                continue
    return iface_list, iface_default

# test valid hostname
def isValidHostname(hostname):
    try:
        if (len(hostname) > 63 or hostname[0] == '-' or hostname[-1] == '-'):
            return False
        allowed = re.compile(r'[a-z0-9\-]*$', re.IGNORECASE)
        if allowed.match(hostname):
            return True
        else:
            return False
    except:
        return False

# test valid domainname
def isValidDomainname(domainname):
    try:
        for label in domainname.split('.'):
            if not isValidHostname(label):
                return False
        return True
    except:
        return False

# test valid ipv4 address
def isValidHostIpv4(ip):
    try:
        ipv4 = IP(ip)
        if not ipv4.version() == 4:
            return False
        ipv4str = IP(ipv4).strNormal(0)
        if (int(ipv4str.split('.')[0]) == 0 or int(ipv4str.split('.')[3]) == 0):
            return False
        for i in ipv4str.split('.'):
            if int(i) > 254:
                return False
        return True
    except:
        return False

# network setup
def networkSetup():
    print('### linuxmuster-mail: network setup')
    # get network interfaces
    iface_list, iface_default = getDefaultIface()
    while True:
        iface = input('Enter network interface to use [' + iface_default + ']: ')
        iface = iface or iface_default
        if iface in iface_list:
            break
        else:
            print("Invalid entry!")
    # ip address & netmask
    default = '10.0.0.3/16'
    while True:
        mailipnet = input('Enter ip address with net or bitmask [' + default + ']: ')
        mailipnet = mailipnet or default
        try:
            n = IP(mailipnet, make_net=True)
            break
        except ValueError:
            print("Invalid entry!")
    mailip = mailipnet.split('/')[0]
    network = IP(n).strNormal(0)
    bitmask = IP(n).strNormal(1).split('/')[1]
    netmask = IP(n).strNormal(2).split('/')[1]
    broadcast = IP(n).strNormal(3).split('-')[1]
    # dns server ip
    o1, o2, o3, o4 = mailip.split('.')
    default = o1 + '.' + o2 + '.' + o3 + '.1'
    while True:
        dnsip = input('Enter dns server ip address [' + default + ']: ')
        dnsip = dnsip or default
        if isValidHostIpv4(dnsip):
            break
        else:
            print("Invalid entry!")
    # gateway ip
    default = o1 + '.' + o2 + '.' + o3 + '.254'
    while True:
        gatewayip = input('Enter gateway ip address [' + default + ']: ')
        gatewayip = gatewayip or default
        if isValidHostIpv4(gatewayip):
            break
        else:
            print("Invalid entry!")
    # domainname
    default = 'linuxmuster.lan'
    while True:
        domainname = input('Enter domainname [' + default + ']: ')
        domainname = domainname or default
        if isValidDomainname(domainname):
            break
        else:
            print("Invalid entry!")
    # patch config templates
    printr('Writing network configuration ... ')
    for f in os.listdir(networktpldir):
        infile = networktpldir + '/' + f
        # read template
        rc, content = readTextfile(infile)
        if not rc:
            return 1
        # extract oufile path from first line
        firstline = re.findall(r'# .*\n', content)[0]
        outfile = firstline.partition(' ')[2].replace('\n', '')
        # replace placeholders
        content = content.replace('@@iface@@', iface)
        content = content.replace('@@mailip@@', mailip)
        content = content.replace('@@netmask@@', netmask)
        content = content.replace('@@network@@', network)
        content = content.replace('@@broadcast@@', broadcast)
        content = content.replace('@@gatewayip@@', gatewayip)
        content = content.replace('@@dnsip@@', dnsip)
        content = content.replace('@@domainname@@', domainname)
        # add date string to content
        content = '# modified by linuxmuster-mail at ' + dtStr() + '\n' + content
        # write outfile
        rc = writeTextfile(outfile, content, 'w')
        if not rc:
            return 1
    # hostname
    if not writeTextfile('/etc/hostname', 'mail', 'w'):
        return 1
    print('Success!')
    # create ssh hostkeys
    hostkey_prefix = '/etc/ssh/ssh_host_'
    crypto_list = ['dsa', 'ecdsa', 'ed25519', 'rsa']
    os.system('rm -f /etc/ssh/*key*')
    print('Creating ssh host keys ...')
    for a in crypto_list:
        printr(' * ' + a + ' host key:')
        try:
            os.system('ssh-keygen -t ' + a + ' -f ' + hostkey_prefix + a + '_key -N ""')
            print(' Success!')
        except:
            print(' Failed!')
            return 1
    return 0

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
    os.system('chmod 750 ' + mailkey)
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
    # only if not on server
#    if mailip != serverip:
#        # hostname
#        rc = writeTextfile('/etc/hostname', 'mail.' + domainname, 'w')
#        rc, content = readTextfile(networktpldir + '/hosts')
#        content = content.replace('@@mailip@@', mailip)
#        content = content.replace('@@domainname@@', domainname)
#        if not writeTextfile(networktpldir + '/hosts', content, 'w'):
#            return 1
#        # interfaces
#        interfaces = '/etc/network/interfaces.d/linuxmuster'
#        rc, content = readTextfile(interfaces)
#        content = re.sub(r'dns-nameservers .*\n', 'dns-nameservers ' + serverip + ' ' + firewallip + '\n', content)
#        content = re.sub(r'dns-search .*\n', 'dns-search ' + domainname + '\n', content)
#        if not writeTextfile(interfaces, content, 'w'):
#            return 1
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


if network == True:
    rc = networkSetup()
elif setup == True:
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
