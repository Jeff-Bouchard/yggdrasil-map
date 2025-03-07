import json
import socket
import sys
import time

#gives the option to get data from an external server instead and send that
#if no options given it will default to localhost instead
if len(sys.argv) == 3:
  socktype = socket.AF_INET
  sockaddr = (sys.argv[1], int(sys.argv[2]))
elif len(sys.argv) == 2:
  socktype = socket.AF_UNIX
  sockaddr = sys.argv[1]
else:
  socktype = socket.AF_UNIX
  sockaddr = "/var/run/yggdrasil.sock"

def getNodeInfoRequest(key):
  return '{{"keepalive":true, "request":"getNodeInfo", "key":"{}"}}'.format(key)

def getSelfRequest(key):
  return '{{"keepalive":true, "request":"debug_remoteGetSelf", "key":"{}"}}'.format(key)

def getPeersRequest(key):
  return '{{"keepalive":true, "request":"debug_remoteGetPeers", "key":"{}"}}'.format(key)

def getDHTRequest(key):
  return '{{"keepalive":true, "request":"debug_remoteGetDHT", "key":"{}"}}'.format(key)

def doRequest(req):
  try:
    ygg = socket.socket(socktype, socket.SOCK_STREAM)
    ygg.connect(sockaddr)
    ygg.send(req)
    data = json.loads(ygg.recv(1024*15))
    return data
  except:
    return None

visited = set() # Add nodes after a successful lookup response
rumored = set() # Add rumors about nodes to ping
timedout = set()
def handleNodeInfoResponse(publicKey, data):
  global visited
  global rumored
  global timedout
  if publicKey in visited: return
  if not data: return
  if 'response' not in data: return
  out = dict()
  for addr,v in data['response'].iteritems():
    out['address'] = addr
    out['nodeinfo'] = v
  selfInfo = doRequest(getSelfRequest(publicKey))
  if 'response' in selfInfo:
    for _,v in selfInfo['response'].iteritems():
      if 'coords' in v:
        out['coords'] = v['coords']
  peerInfo = doRequest(getPeersRequest(publicKey))
  if 'response' in peerInfo:
    for _,v in peerInfo['response'].iteritems():
      if 'keys' not in v: continue
      peers = v['keys']
      for key in peers:
        if key in visited: continue
        if key in timedout: continue
        rumored.add(key)
      out['peers'] = peers
  dhtInfo = doRequest(getDHTRequest(publicKey))
  if 'response' in dhtInfo:
    for _,v in dhtInfo['response'].iteritems():
      if 'keys' in v:
        dht = v['keys']
        for key in dht:
          if key in visited: continue
          if key in timedout: continue
          rumored.add(key)
        out['dht'] = dht
  out['time'] = time.time()
  if len(visited) > 0: sys.stdout.write(",\n")
  sys.stdout.write('"{}": {}'.format(publicKey, json.dumps(out)))
  sys.stdout.flush()
  visited.add(publicKey)
# End handleResponse

# Get self info
selfInfo = doRequest('{"keepalive":true, "request":"getSelf"}')
for k,v in selfInfo['response']['self'].iteritems(): rumored.add(v['key'])

# Initialize dicts of visited/rumored nodes
#for k,v in selfInfo['response']['self'].iteritems(): rumored[k] = v

# Loop over rumored nodes and ping them, adding to visited if they respond
print '{"yggnodes": {'
while len(rumored) > 0:
  for k in rumored:
    handleNodeInfoResponse(k, doRequest(getNodeInfoRequest(k)))
    break
  rumored.remove(k)
print '\n}}'
#End

# TODO do something with the results

#print visited
#print timedout
