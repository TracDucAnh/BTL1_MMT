// Simple client script for the WeApRous sample chat
(function(){
  const trackerBase = window.TRACKER_BASE || (window.location.protocol + '//' + window.location.hostname + ':8000');

  const $ = id => document.getElementById(id);

  async function register() {
    const port = $('port').value || '9001';
    const ip = window.location.hostname;  

    try {
      const body = `ip=${ip}&port=${port}`;
      const res = await fetch(trackerBase + '/submit-info', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: body,
      });
      const txt = await res.text();
      console.log('register result', txt);
      appendMessage('system', 'Registered with tracker');
      await getList();
    } catch (e) {
      console.error('register failed', e);
      appendMessage('system', 'Register failed: ' + e.message);
    }
  }

  async function getList() {
    try {
      const res = await fetch(trackerBase + '/get-list');
      const txt = await res.text();
      const obj = JSON.parse(txt);
      const list = obj.peers || [];
      renderPeers(list);
    } catch (e) {
      console.error('get-peers failed', e);
      appendMessage('system', 'get-list failed: ' + e.message);
    }
  }

function renderPeers(peers) {
  const ul = $('peerList');
  ul.innerHTML = '';

  if (!peers || peers.length === 0) {
    const li = document.createElement('li');
    li.textContent = 'No other peers online.';
    li.style.color = '#777';
    ul.appendChild(li);
    return;
  }

  peers.forEach(p => {
    const li = document.createElement('li');
    li.textContent = `${p.ip}:${p.port}`;
    li.style.padding = '8px';
    li.style.border = '1px solid #ccc';
    li.style.borderRadius = '6px';
    li.style.marginBottom = '6px';
    li.style.cursor = 'pointer';
    li.style.backgroundColor = '#f9f9f9';
    li.addEventListener('mouseenter', () => li.style.backgroundColor = '#e0f2ff');
    li.addEventListener('mouseleave', () => li.style.backgroundColor = '#f9f9f9');
    li.addEventListener('click', () => {
      // highlight selection
      Array.from(ul.children).forEach(el => el.style.borderColor = '#ccc');
      li.style.borderColor = '#007bff';

      // call connectPeer
      connectPeer(p);
    });
    ul.appendChild(li);
  });
}


  async function connectPeer(peer) {
    try {
      const res = await fetch(trackerBase + '/connect-peer', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          target_ip: peer.ip,
          target_port: peer.port
        })
      });

      const txt = await res.text();
      console.log('connect-peer result', txt);
      appendMessage('system', `Connected to peer ${peer.ip}:${peer.port}`);
    } catch (e) {
      console.error('connect-peer failed', e);
      appendMessage('system', 'connect-peer failed: ' + e.message);
    }
  }

  function appendMessage(sender, text) {
    const box = $('messages');
    const el = document.createElement('div');
    el.innerHTML = `<strong>${sender}</strong>: ${text}`;
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
  }

  async function sendMessage() {
    const msg = $('messageInput').value;
    if (!msg) return;
    appendMessage('me', msg);
    // broadcast to peers via HTTP POST to /send-peer (best-effort)
    try {
      const res = await fetch(trackerBase + '/get-list');
      const txt = await res.text();
      const obj = JSON.parse(txt);
      const peers = obj.peers || [];
      peers.forEach(async p => {
        try {
          const url = `http://${p.ip}:${p.port}/send-peer`;
          await fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: `from=${encodeURIComponent(window.location.hostname)}&msg=${encodeURIComponent(msg)}`
          });
        } catch (e) {
          console.debug('send to peer failed', p, e.message);
        }
      });
    } catch (e) {
      console.error('broadcast failed', e);
    }
    $('messageInput').value = '';
  }

  // wire UI
  window.addEventListener('load', () => {
    $('btnRegister').addEventListener('click', register);
    $('btnRefresh').addEventListener('click', refreshPeers);
    $('btnSend').addEventListener('click', sendMessage);
  });

})();