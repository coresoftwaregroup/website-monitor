"""
@author Kyle Williams <kwilliams@psu.edu>
@date Nov 12, 2013

A simple Web service to monitor a set of websites

Run: python website-check.py port "site1" "assert1" ["site2" "assert2" ... ]
or: python website-check.py port servers.txt (see README)
"""

import web
import requests
import sys
import string
import thread
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from datetime import datetime
from repeattimer import RepeatTimer

urls = (
'/', 'Index',
)

poll_interval = 300 #How often the sites should be polled
max_fails = 10 #Max number of fails before notification
servers = []
app = web.application(urls, globals(), servers)

gmail_user = ''
gmail_pwd = ''
recipients = ['someone@example.com', 'someone@example.com']

def mail(to, subject, text):
   msg = MIMEMultipart()
   msg['From'] = gmail_user
   msg['To'] = ", ".join(recipients)
   msg['Subject'] = subject
   msg.attach(MIMEText(text))  
   mailServer = smtplib.SMTP("smtp.gmail.com", 587)
   mailServer.ehlo()
   mailServer.starttls()
   mailServer.ehlo()
   mailServer.login(gmail_user, gmail_pwd)
   mailServer.sendmail(gmail_user, to, msg.as_string())   
   mailServer.close()

def check_servers():
    """ A static method to check the status of all servers """
    for server in servers: 
      thread.start_new_thread(server.check_status, ())
      
class Server:
  def __init__(self, url, assert_string=""):
    self.url = url
    self.fails = 0
    self.status_code = 0
    self.status = ''
    self.last_checked=datetime.min
    self.notified_fail=False
    self.assert_string=assert_string
    self.assert_pass=False
    
  def check_status(self):
    """ Checks the status of the server """
    self.last_checked = datetime.now()
    try:
      r = requests.get(self.url, timeout=5)
      self.status_code = r.status_code
      if self.status_code == 200:
	if self.assert_string in r.text:
	  self.status = 'OK'
	  self.fails = 0
	  self.notified_fail=False
	  self.assert_pass=True
	else:
	  self.status = 'Assert Failed'
	  self.fails += 1
	  self.assert_pass=False
      else:
	self.fails += 1
	self.status = 'ERROR'
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
      self.status_code = 500
      self.status = str(e)
      self.fails += 1
    
    if self.fails >= max_fails and self.notified_fail is False:
      self.notified_fail = True
      mail(recipients, 'Server down', str("This is an automated message. Server at " + self.url + " is down. Last checked at " + str(self.last_checked)))
      
    print str(self.last_checked) + ": " + self.url + " - " + self.status
    
    return self.status_code, self.last_checked
    
class Index:

  def GET(self):    
    """ The display page """
    web.header('Content-Type','text/html; charset=utf-8')
    web.header('Content-Language','en') 
    html = """<html><body><h3>Status of Web Servers</h3>"""
    html += "<table border=1><tr><td><b>Server</b></td><td><b>Status</b></td><td><b>Assert String</b></td><td><b>Assert Passed</b></td><td><b>Last Checked</b></td></tr>"
    for server in servers:
      if server.status_code == 200:
	scolor = 'green'
      else:
	scolor = 'red'
      if server.assert_pass is True:
	acolor = 'green'
      else:
	acolor = 'red'
      html += '<tr><td><a href=\'' + server.url + '\'>' + server.url + '</a></td><td><font color=' + scolor + '>' + str(server.status_code) + ' ' + server.status + '</font></td><td>' + server.assert_string + '</td><td><font color=' + acolor + '>' + str(server.assert_pass) + '</font></td><td>' + str(server.last_checked) + '</td></tr>'
    html += """</table>"""
    html += """<form method="POST" action="">
                <input type="submit" value="Check Status"/>
                </form>
                </body></html>"""
    return html
    
  def POST(self):
    """ Manual check """
    check_servers()
    raise web.seeother('/')
    
if __name__ == "__main__":
  
  if len(sys.argv) == 3:
    lines = (line.rstrip('\n') for line in open(sys.argv[2]))
    for line in lines:
      url, assert_string = string.split(line,',')
      print url + " " + assert_string
      servers.append(Server(url, assert_string))
  else:
    for url,assert_string in zip(sys.argv[2::2], sys.argv[3::2]):
      print url + " " + assert_string
      servers.append(Server(url, assert_string))
  check_servers()
  timerName = RepeatTimer(poll_interval, check_servers) # Repeatedly check servers
  timerName.start()
  app.run()
  
