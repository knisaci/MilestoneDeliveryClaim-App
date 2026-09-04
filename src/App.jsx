import { useState, useEffect } from 'react'
import { createClient } from 'genlayer-js'
import { testnetBradbury } from 'genlayer-js/chains'
import './App.css'

const CONTRACT = '0x3fdfb8bfb3E5EfFa8f6048b52e072A012919adbd'
const readClient = createClient({ chain: testnetBradbury })

function short(addr) {
  if (!addr) return '—'
  const s = String(addr)
  return s.slice(0, 6) + '…' + s.slice(-4)
}

function gen(wei) {
  return (Number(wei || 0) / 1e18).toFixed(4) + ' GEN'
}

function App() {
  const [account, setAccount] = useState(null)
  const [c, setC] = useState(null)
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [amount, setAmount] = useState('0.1')

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const result = await readClient.readContract({
        address: CONTRACT,
        functionName: 'get_claim',
        args: [],
      })
      setC(result)
    } catch (e) {
      console.error(e)
    }
  }

  async function connect() {
    if (!window.ethereum) return alert('Install MetaMask')
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' })
    setAccount(accounts[0])
  }

  async function sendTx(name, value, waitMs, okMsg) {
    if (!account) return alert('Connect wallet first')
    setLoading(true)
    setStatus('Sending ' + name + '…')
    try {
      const client = createClient({ chain: testnetBradbury, account, provider: window.ethereum })
      try { await client.connect('testnetBradbury') } catch {}
      const tx = await client.writeContract({
        address: CONTRACT,
        functionName: name,
        args: [],
        value,
      })
      setStatus('Tx ' + String(tx).slice(0, 12) + '… waiting')
      setTimeout(() => { load(); setLoading(false); setStatus(okMsg) }, waitMs)
    } catch (e) {
      setStatus('Error: ' + (e.message || 'failed'))
      setLoading(false)
    }
  }

  const wei = () => BigInt(Math.floor(Number(amount) * 1e18))
  const isClient = account && c && account.toLowerCase() === String(c.client || '').toLowerCase()
  const isWorker = account && c && account.toLowerCase() === String(c.worker || '').toLowerCase()
  const pill = c?.status || 'loading'

  return (
    <div className="app">
      <div className="glow" />
      <header>
        <div className="badge">GenLayer · Sealed milestone escrow</div>
        <h1>Milestone Delivery Claim</h1>
        <p className="sub">Client names the evidence URL. Worker seals a snapshot + hash. Resolve uses only that snapshot. A seal after the deadline cannot pay.</p>
      </header>

      <section className="card hero">
        <div className={'pill ' + pill}>{pill}</div>
        <p className="question">{c?.milestone_description || 'Loading…'}</p>
        {c?.evidence_url && <a className="link" href={c.evidence_url} target="_blank" rel="noreferrer">{c.evidence_url}</a>}
      </section>

      <section className="grid2">
        <div className="card">
          <h2>Escrow</h2>
          <div className="stat">{c ? gen(c.escrow_balance) : '—'}</div>
          <div className="rows">
            <div><span>Payment</span><b>{c ? gen(c.payment_amount) : '—'}</b></div>
            <div><span>Deadline</span><b>{c?.deadline || '—'}</b></div>
            <div><span>Deadline passed</span><b>{c?.deadline_passed ? 'yes' : 'no'}</b></div>
          </div>
        </div>
        <div className="card">
          <h2>Sealed evidence</h2>
          <div className="rows">
            <div><span>Sealed</span><b>{c?.evidence_sealed ? 'yes' : 'no'}</b></div>
            <div><span>On time</span><b>{c?.sealed_on_time ? 'yes' : 'no'}</b></div>
            <div><span>Sealed unix</span><b>{c ? String(c.sealed_unix) : '—'}</b></div>
            <div><span>Hash</span><b>{c?.evidence_hash ? String(c.evidence_hash).slice(0, 12) + '…' : '—'}</b></div>
          </div>
        </div>
      </section>

      <section className="card">
        <h2>Parties / resolution</h2>
        <div className="rows">
          <div><span>Client</span><b>{short(c?.client)}</b></div>
          <div><span>Worker</span><b>{short(c?.worker)}</b></div>
          <div><span>Delivery</span><b>{c?.delivery_status || '—'}</b></div>
          <div><span>Paid / refunded</span><b>{c?.is_paid ? 'paid' : c?.is_refunded ? 'refunded' : 'no'}</b></div>
        </div>
        <p className="note">{c?.note || 'No note yet.'}</p>
      </section>

      <section className="card">
        <h2>Actions</h2>
        {!account ? (
          <button className="primary" onClick={connect}>Connect wallet</button>
        ) : (
          <>
            <p className="wallet">{short(account)}{isClient ? ' · client' : ''}{isWorker ? ' · worker' : ''}</p>
            <div className="action">
              <h3>Fund</h3>
              <div className="row">
                <input type="number" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} />
                <button className="primary" disabled={loading || !isClient} onClick={() => sendTx('fund', wei(), 25000, 'Funded')}>Fund</button>
              </div>
            </div>
            {c && !c.evidence_sealed && !c.has_resolved && (
              <div className="action">
                <h3>Seal evidence</h3>
                <p className="hint">Worker only. Fetches the frozen URL once, stores snapshot + sha256. Cannot be changed.</p>
                <button className="primary" disabled={loading || !isWorker} onClick={() => sendTx('seal_evidence', 0n, 90000, 'Evidence sealed')}>Seal evidence</button>
              </div>
            )}
            {c && c.evidence_sealed && !c.has_resolved && (
              <div className="action">
                <h3>Resolve</h3>
                <p className="hint">Uses the sealed snapshot only. Late seals cannot pay.</p>
                <button className="primary" disabled={loading} onClick={() => sendTx('resolve', 0n, 90000, 'Resolve sent')}>Resolve</button>
              </div>
            )}
            {c?.delivery_status === 'delivered' && !c.is_paid && (
              <button className="primary" disabled={loading} onClick={() => sendTx('pay_worker', 0n, 25000, 'Worker paid')}>Pay worker</button>
            )}
            {c && ['not_delivered', 'unknown'].includes(c.delivery_status) && !c.is_refunded && (
              <div className="action">
                <p className="hint">{c.deadline_passed ? 'Deadline reached.' : 'Refund blocked until deadline.'}</p>
                <button disabled={loading || !c.deadline_passed} onClick={() => sendTx('refund_client', 0n, 25000, 'Refunded')}>Refund client</button>
              </div>
            )}
            {c?.is_paid && Number(c.escrow_balance) > 0 && (
              <button className="primary" disabled={loading || !isClient} onClick={() => sendTx('withdraw_remainder', 0n, 25000, 'Remainder withdrawn')}>Withdraw remainder</button>
            )}
          </>
        )}
        {status && <p className="status">{status}</p>}
      </section>

      <footer>
        <div>Contract · {CONTRACT}</div>
        <div>Testnet Bradbury · sealed snapshot + deadline</div>
      </footer>
    </div>
  )
}

export default App
