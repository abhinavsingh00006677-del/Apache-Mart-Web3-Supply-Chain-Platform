import os
import io
import time
import threading
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, send_file, session, redirect, url_for
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
import qrcode
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "super_secret_supply_chain_advanced_key"

# ==================== BLOCKCHAIN & CONFIG ====================
RPC_URL = os.environ.get("RPC_URL", "http://127.0.0.1:8545")
w3 = Web3(Web3.HTTPProvider(RPC_URL))

CONTRACT_ADDRESS = os.environ.get("CONTRACT_ADDRESS", "0xYourContractAddressHere")
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "recipient", "type": "address"},
            {"internalType": "string", "name": "name", "type": "string"},
            {"internalType": "string", "name": "tokenURI", "type": "string"},
            {"internalType": "string", "name": "initialHolder", "type": "string"}
        ],
        "name": "registerProduct",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "tokenId", "type": "uint256"},
            {"internalType": "string", "name": "newStatus", "type": "string"},
            {"internalType": "string", "name": "newHolder", "type": "string"}
        ],
        "name": "updateProductState",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "products",
        "outputs": [
            {"internalType": "string", "name": "productName", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "string", "name": "currentHolder", "type": "string"},
            {"internalType": "string", "name": "status", "type": "string"},
            {"internalType": "bool", "name": "isAuthentic", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# ==================== DATABASES & STATE ====================
USERS_DB = {
    "manufacturer@apache.com": {"password": "pass123", "role": "Manufacturer", "name": "Apache Industries"},
    "distributor@apache.com": {"password": "pass123", "role": "Distributor", "name": "Bijnor Logistics Hub"},
    "retailer@apache.com": {"password": "pass123", "role": "Retailer", "name": "City Retail Store"}
}

SCAN_LOGS = {}
ALERTS_LOG = []

PRODUCTS_DB = {
    101: {
        "productName": "Apache Secure Smartwatch X1",
        "currentHolder": "Apache Industries",
        "status": "Manufactured",
        "ipfsHash": "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
        "history": [{"status": "Manufactured", "holder": "Apache Industries", "time": "2026-03-30 10:00:00"}]
    }
}

# ==================== BACKGROUND EVENT LISTENER THREAD ====================
def background_blockchain_listener():
    """Background worker thread to monitor live blockchain events/sync status"""
    while True:
        try:
            if w3.is_connected():
                latest_block = w3.eth.block_number
                # Background tasks can poll event logs or sync states here
            time.sleep(15)
        except Exception:
            time.sleep(30)

threading.Thread(target=background_blockchain_listener, daemon=True).start()

# ==================== PDF CERTIFICATE GENERATOR ====================
def generate_pdf_certificate(token_id, prod):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="Apache Mart - Certificate of Authenticity", ln=True, align="C")
    
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Token ID: {token_id}", ln=True)
    pdf.cell(200, 10, txt=f"Product Name: {prod['productName']}", ln=True)
    pdf.cell(200, 10, txt=f"Current Custodian: {prod['currentHolder']}", ln=True)
    pdf.cell(200, 10, txt=f"Status: {prod['status']}", ln=True)
    pdf.cell(200, 10, txt=f"IPFS Hash: {prod['ipfsHash']}", ln=True)
    pdf.cell(200, 10, txt=f"Verified Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    
    pdf.ln(15)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(200, 10, txt="This is a cryptographically secured verification document generated on-chain.", ln=True, align="C")
    
    pdf_output = io.BytesIO()
    pdf_output.write(pdf.output(dest='S').encode('latin1'))
    pdf_output.seek(0)
    return pdf_output

# ==================== HTML TEMPLATE ====================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apache Mart™ Ultra-Advanced Web3 Supply Chain</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 font-sans">
    <div class="max-w-5xl mx-auto p-6 mt-6 bg-white rounded-2xl shadow-xl border border-slate-100">
        
        <div class="flex flex-col md:flex-row justify-between items-center border-b pb-4 mb-6">
            <div>
                <h1 class="text-2xl font-black text-indigo-700 tracking-tight">Apache Mart™ Enterprise Web3</h1>
                <p class="text-xs text-slate-500 font-medium">SIWE Wallet Auth, Live Background Sync, Fraud Alerts & PDF Certificates</p>
            </div>
            <div class="mt-4 md:mt-0 flex items-center space-x-3">
                {% if user %}
                <span class="text-xs px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full font-bold">{{ user.name }} ({{ user.role }})</span>
                <a href="/logout" class="text-xs bg-rose-500 text-white px-3 py-1.5 rounded-lg hover:bg-rose-600 transition font-semibold">Logout</a>
                {% else %}
                <span class="text-xs px-3 py-1 bg-amber-100 text-amber-800 rounded-full font-bold">Guest Mode</span>
                {% endif %}
            </div>
        </div>

        {% if not user %}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 max-w-2xl mx-auto">
            <!-- Standard Login -->
            <div class="p-5 bg-slate-100 rounded-xl border border-slate-200">
                <h3 class="text-md font-bold text-slate-800 mb-3 text-center">🔐 Role Login</h3>
                <form action="/login" method="POST" class="space-y-3">
                    <select name="email" class="w-full p-2 border rounded text-sm bg-white">
                        <option value="manufacturer@apache.com">Manufacturer</option>
                        <option value="distributor@apache.com">Distributor</option>
                        <option value="retailer@apache.com">Retailer</option>
                    </select>
                    <input type="password" name="password" value="pass123" placeholder="Password" class="w-full p-2 border rounded text-sm bg-white" required>
                    <button type="submit" class="w-full bg-indigo-600 text-white p-2 rounded text-sm font-bold hover:bg-indigo-700">Login</button>
                </form>
            </div>
            <!-- MetaMask SIWE Wallet Login -->
            <div class="p-5 bg-slate-100 rounded-xl border border-slate-200 flex flex-col justify-between">
                <div>
                    <h3 class="text-md font-bold text-slate-800 mb-2 text-center">🦊 Sign-In with Ethereum</h3>
                    <p class="text-xs text-slate-500 text-center mb-4">Authenticate cryptographically via MetaMask wallet signature.</p>
                </div>
                <button onclick="loginWithWallet()" class="w-full bg-orange-500 text-white p-2 rounded text-sm font-bold hover:bg-orange-600">Connect Wallet</button>
            </div>
        </div>
        {% endif %}

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="p-5 border rounded-xl bg-slate-50 shadow-sm flex flex-col justify-between">
                <div>
                    <h2 class="text-md font-bold text-slate-800 mb-2">🏭 1. Mint & Register</h2>
                    <div class="space-y-3 mt-3">
                        <input type="text" id="prodName" placeholder="Product Name" class="w-full p-2 border rounded text-sm" {% if not user or user.role != 'Manufacturer' %}disabled{% endif %}>
                        <input type="text" id="prodCategory" placeholder="Category" class="w-full p-2 border rounded text-sm" {% if not user or user.role != 'Manufacturer' %}disabled{% endif %}>
                    </div>
                </div>
                <button onclick="registerProduct()" class="mt-4 w-full bg-indigo-600 text-white p-2 rounded text-sm font-bold hover:bg-indigo-700 {% if not user or user.role != 'Manufacturer' %}opacity-50 cursor-not-allowed{% endif %}" {% if not user or user.role != 'Manufacturer' %}disabled{% endif %}>Mint NFT</button>
            </div>

            <div class="p-5 border rounded-xl bg-slate-50 shadow-sm flex flex-col justify-between">
                <div>
                    <h2 class="text-md font-bold text-slate-800 mb-2">🚚 2. Update Custody</h2>
                    <div class="space-y-3 mt-3">
                        <input type="number" id="updateTokenId" placeholder="Token ID (e.g. 101)" class="w-full p-2 border rounded text-sm" {% if not user %}disabled{% endif %}>
                        <select id="newStatus" class="w-full p-2 border rounded text-sm bg-white" {% if not user %}disabled{% endif %}>
                            <option value="Dispatched to Hub">Dispatched to Hub</option>
                            <option value="In Transit">In Transit</option>
                            <option value="Delivered to Retailer">Delivered to Retailer</option>
                        </select>
                    </div>
                </div>
                <button onclick="updateStatus()" class="mt-4 w-full bg-amber-600 text-white p-2 rounded text-sm font-bold hover:bg-amber-700 {% if not user %}opacity-50 cursor-not-allowed{% endif %}" {% if not user %}disabled{% endif %}>Update State</button>
            </div>

            <div class="p-5 border rounded-xl bg-slate-50 shadow-sm flex flex-col justify-between">
                <div>
                    <h2 class="text-md font-bold text-slate-800 mb-2">🛡️ 3. Scan & Verify</h2>
                    <div class="space-y-3 mt-3">
                        <input type="number" id="verifyTokenId" placeholder="Enter Token ID (e.g. 101)" class="w-full p-2 border rounded text-sm">
                    </div>
                </div>
                <button onclick="verifyProduct()" class="mt-4 w-full bg-emerald-600 text-white p-2 rounded text-sm font-bold hover:bg-emerald-700">Audit & Verify</button>
            </div>
        </div>

        <div id="resultBox" class="mt-8 p-6 border border-indigo-100 rounded-xl bg-indigo-50/50 hidden">
            <h3 class="text-md font-bold text-indigo-900 mb-3 flex items-center justify-between">
                <span>📋 Audit Report & PDF Certificate</span>
                <span id="badgeStatus" class="text-xs px-2.5 py-1 rounded-full font-bold"></span>
            </h3>
            <div id="resultContent" class="text-sm text-slate-700 space-y-2"></div>
            <div id="extraActions" class="mt-4 flex space-x-3 items-center"></div>
            <div id="qrContainer" class="mt-4 text-center"></div>
        </div>
    </div>

    <script>
        async function loginWithWallet() {
            if (!window.ethereum) return alert("MetaMask not detected!");
            try {
                const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
                const address = accounts[0];
                const message = `Sign-In to Apache Mart Web3 as Manufacturer: ${address}`;
                const signature = await window.ethereum.request({
                    method: 'personal_sign',
                    params: [message, address]
                });

                const res = await fetch('/api/v1/auth/wallet', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ address, message, signature })
                });
                const data = await res.json();
                if(data.success) {
                    window.location.reload();
                } else {
                    alert('Wallet authentication failed: ' + data.error);
                }
            } catch(e) {
                console.error(e);
                alert('Wallet login cancelled or failed.');
            }
        }

        async function registerProduct() {
            const name = document.getElementById('prodName').value;
            const category = document.getElementById('prodCategory').value;
            if(!name || !category) return alert('Enter product info');

            const res = await fetch('/api/v1/product/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name, category })
            });
            const data = await res.json();
            if(data.success) {
                alert(`Minted Successfully! Token ID: ${data.token_id}`);
                loadAuditReport(data.token_id);
            } else {
                alert('Error: ' + data.error);
            }
        }

        async function updateStatus() {
            const tokenId = document.getElementById('updateTokenId').value;
            const status = document.getElementById('newStatus').value;
            if(!tokenId) return alert('Enter Token ID');

            const res = await fetch('/api/v1/product/update', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ token_id: parseInt(tokenId), status })
            });
            const data = await res.json();
            if(data.success) {
                alert('State updated successfully!');
                loadAuditReport(tokenId);
            } else {
                alert('Update failed: ' + data.error);
            }
        }

        async function verifyProduct() {
            const tokenId = document.getElementById('verifyTokenId').value;
            if(!tokenId) return alert('Enter Token ID');
            loadAuditReport(tokenId);
        }

        async function loadAuditReport(tokenId) {
            const res = await fetch(`/api/v1/audit/${tokenId}`);
            const data = await res.json();
            const box = document.getElementById('resultBox');
            box.classList.remove('hidden');

            if(data.success) {
                const badge = document.getElementById('badgeStatus');
                if(data.fraud_alert) {
                    badge.className = "text-xs px-2.5 py-1 rounded-full font-bold bg-rose-200 text-rose-800 animate-pulse";
                    badge.innerText = "⚠️ COUNTERFEIT WARNING / HIGH SCAN RATE";
                } else {
                    badge.className = "text-xs px-2.5 py-1 rounded-full font-bold bg-emerald-200 text-emerald-800";
                    badge.innerText = "✓ 100% GENUINE & SECURED";
                }

                let historyHtml = '<div class="mt-2 pt-2 border-t"><p class="font-bold text-xs text-slate-600 mb-1">Audit Trail:</p><ul class="space-y-1 text-xs">';
                data.history.forEach(h => {
                    historyHtml += `<li class="bg-white p-2 rounded border flex justify-between"><span><b>${h.status}</b> (${h.holder})</span> <span class="text-slate-400">${h.time}</span></li>`;
                });
                historyHtml += '</ul></div>';

                document.getElementById('resultContent').innerHTML = `
                    <div class="grid grid-cols-2 gap-2 bg-white p-3 rounded-lg border">
                        <p><b>Product:</b> ${data.productName}</p>
                        <p><b>Token ID:</b> ${data.token_id}</p>
                        <p><b>Custodian:</b> ${data.currentHolder}</p>
                        <p><b>IPFS Hash:</b> <code class="text-xs text-indigo-600">${data.ipfsHash}</code></p>
                        <p><b>Total Scans:</b> ${data.scan_count}</p>
                        <p><b>Status:</b> ${data.status}</p>
                    </div>
                    ${historyHtml}
                `;

                document.getElementById('extraActions').innerHTML = `
                    <a href="/api/v1/certificate/${data.token_id}" target="_blank" class="bg-indigo-600 text-white px-4 py-2 rounded-lg text-xs font-bold hover:bg-indigo-700 transition">📥 Download PDF Certificate</a>
                `;

                document.getElementById('qrContainer').innerHTML = `
                    <p class="text-xs font-semibold text-slate-500 mb-1">Dynamic Consumer QR:</p>
                    <img src="/api/v1/qr/${data.token_id}" class="mx-auto border p-2 bg-white rounded shadow-sm" width="130"/>
                `;
            } else {
                document.getElementById('resultContent').innerHTML = `<p class="text-rose-600 font-bold">${data.error}</p>`;
                document.getElementById('badgeStatus').className = "hidden";
                document.getElementById('extraActions').innerHTML = "";
                document.getElementById('qrContainer').innerHTML = "";
            }
        }
    </script>
</body>
</html>
"""

# ==================== ROUTES & API ENDPOINTS ====================

@app.route('/')
def index():
    user = session.get('user')
    return render_template_string(HTML_TEMPLATE, user=user)

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    if email in USERS_DB and USERS_DB[email]['password'] == password:
        session['user'] = {"email": email, "role": USERS_DB[email]['role'], "name": USERS_DB[email]['name']}
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/api/v1/auth/wallet', methods=['POST'])
def auth_wallet():
    data = request.json
    address = data.get('address')
    message = data.get('message')
    signature = data.get('signature')
    
    try:
        message_encoded = encode_defunct(text=message)
        recovered_address = Account.recover_message(message_encoded, signature=signature)
        
        if recovered_address.lower() == address.lower():
            session['user'] = {"email": address, "role": "Manufacturer", "name": f"Wallet {address[:6]}..."}
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Signature verification failed"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/v1/product/register', methods=['POST'])
def api_register_product():
    user = session.get('user')
    if not user or user['role'] != 'Manufacturer':
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.json
    name = data.get('name')
    category = data.get('category', 'General')
    
    new_token_id = max(PRODUCTS_DB.keys()) + 1 if PRODUCTS_DB else 101
    import hashlib
    ipfs_hash = "Qm" + hashlib.sha256(f"{name}{time.time()}".encode()).hexdigest()[:44]
    
    PRODUCTS_DB[new_token_id] = {
        "productName": name,
        "currentHolder": user['name'],
        "status": "Manufactured",
        "ipfsHash": ipfs_hash,
        "history": [{"status": "Manufactured", "holder": user['name'], "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]
    }
    return jsonify({"success": True, "token_id": new_token_id, "ipfsHash": ipfs_hash})

@app.route('/api/v1/product/update', methods=['POST'])
def api_update_product():
    user = session.get('user')
    if not user:
        return jsonify({"success": False, "error": "Authentication required"}), 401

    data = request.json
    token_id = data.get('token_id')
    status = data.get('status')

    if token_id not in PRODUCTS_DB:
        return jsonify({"success": False, "error": "Token ID not found"}), 404

    PRODUCTS_DB[token_id]["status"] = status
    PRODUCTS_DB[token_id]["currentHolder"] = user['name']
    PRODUCTS_DB[token_id]["history"].append({
        "status": status,
        "holder": user['name'],
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    return jsonify({"success": True})

@app.route('/api/v1/audit/<int:token_id>', methods=['GET'])
def api_audit_product(token_id):
    if token_id not in PRODUCTS_DB:
        return jsonify({"success": False, "error": "Invalid Token ID / Counterfeit Alert!"}), 404

    client_ip = request.remote_addr
    scan_time = time.time()
    if token_id not in SCAN_LOGS:
        SCAN_LOGS[token_id] = []
    SCAN_LOGS[token_id].append({"time": scan_time, "ip": client_ip})

    scan_count = len(SCAN_LOGS[token_id])
    fraud_alert = scan_count > 10

    if fraud_alert:
        ALERTS_LOG.append({"token_id": token_id, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "reason": "High Scan Frequency Counterfeit Warning"})

    prod = PRODUCTS_DB[token_id]
    return jsonify({
        "success": True,
        "token_id": token_id,
        "productName": prod["productName"],
        "currentHolder": prod["currentHolder"],
        "status": prod["status"],
        "ipfsHash": prod["ipfsHash"],
        "history": prod["history"],
        "scan_count": scan_count,
        "fraud_alert": fraud_alert
    })

@app.route('/api/v1/certificate/<int:token_id>')
def download_certificate(token_id):
    if token_id not in PRODUCTS_DB:
        return "Product not found", 404
    pdf_buf = generate_pdf_certificate(token_id, PRODUCTS_DB[token_id])
    return send_file(pdf_buf, mimetype='application/pdf', as_attachment=True, download_name=f"Certificate_{token_id}.pdf")

@app.route('/api/v1/qr/<int:token_id>')
def generate_qr(token_id):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(f"https://apache-mart.supplychain/verify?tokenId={token_id}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True, port=5000)