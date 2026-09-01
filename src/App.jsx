import { useState, useEffect } from 'react'
import { createClient } from 'genlayer-js'
import { testnetBradbury } from 'genlayer-js/chains'
import './App.css'

const CONTRACT = '0xdD44E5d445259009b8113482E5131479C00B5315'
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
  const pill = c?.status || 'loading'

  return (
    <div className="app">
      <div className="glow" />
      <header>
        <div className="badge">GenLayer · Milestone escrow</div>
        <h1>Milestone Delivery Claim</h1>
        <p className="sub">Client locks GEN. Validators check public evidence. Worker is paid on delivery. Refunds wait until the deadline. Leftover capital returns to the client.</p>
      </header>

      <section className="card hero">
        <div className={'pill ' + pill}>{pill}</div>
        <p className="question">{c?.milestone_description || 'Loading…'}</p>
        {c?.evidence_url && (
          <a className="link" href={c.evidence_url} target="_blank" rel="noreferrer">{c.evidence_url}</a>
        )}
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
          <h2>Parties</h2>
          <div className="rows">
            <div><span>Client</span><b>{short(c?.client)}</b></div>
            <div><span>Worker</span><b>{short(c?.worker)}</b></div>
            <div><span>Paid</span><b>{c?.is_paid ? 'yes' : 'no'}</b></div>
            <div><span>Refunded</span><b>{c?.is_refunded ? 'yes' : 'no'}</b></div>
          </div>
        </div>
      </section>

      <section className="card">
        <h2>Resolution</h2>
        <div className="rows">
          <div><span>Delivery</span><b>{c?.delivery_status || '—'}</b></div>
          <div><span>Resolved</span><b>{c?.has_resolved ? 'yes' : 'no'}</b></div>
        </div>
        <p className="note">{c?.note || 'No note yet.'}</p>
      </section>

      <section className="card">
        <h2>Actions</h2>
        {!account ? (
          <button className="primary" onClick={connect}>Connect wallet</button>
        ) : (
          <>
            <p className="wallet">{short(account)}{isClient ? ' · client' : ''}</p>
            <div className="action">
              <h3>Fund as client</h3>
              <div className="row">
                <input type="number" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} />
                <button className="primary" disabled={loading || !isClient} onClick={() => sendTx('fund', wei(), 25000, 'Funded')}>Fund</button>
              </div>
            </div>
            {c && !c.has_resolved && (
              <div className="action">
                <h3>Resolve</h3>
                <p className="hint">Validators fetch the evidence URL. Refund stays blocked until deadline_unix.</p>
                <button className="primary" disabled={loading} onClick={() => sendTx('resolve', 0n, 90000, 'Resolve sent')}>Resolve</button>
              </div>
            )}
            {c?.delivery_status === 'delivered' && !c.is_paid && (
              <div className="action">
                <h3>Pay worker</h3>
                <button className="primary" disabled={loading} onClick={() => sendTx('pay_worker', 0n, 25000, 'Worker paid')}>Pay worker</button>
              </div>
            )}
            {c && ['not_delivered', 'unknown'].includes(c.delivery_status) && !c.is_refunded && (
              <div className="action">
                <h3>Refund client</h3>
                <p className="hint">{c.deadline_passed ? 'Deadline reached.' : 'Blocked until deadline.'}</p>
                <button disabled={loading || !c.deadline_passed} onClick={() => sendTx('refund_client', 0n, 25000, 'Refunded')}>Refund client</button>
              </div>
            )}
            {c?.is_paid && Number(c.escrow_balance) > 0 && (
              <div className="action">
                <h3>Withdraw remainder</h3>
                <button className="primary" disabled={loading || !isClient} onClick={() => sendTx('withdraw_remainder', 0n, 25000, 'Remainder withdrawn')}>Withdraw remainder</button>
              </div>
            )}
          </>
        )}
        {status && <p className="status">{status}</p>}
      </section>

      <footer>
        <div>Contract · {CONTRACT}</div>
        <div>Testnet Bradbury</div>
      </footer>
    </div>
  )
}

export default App
