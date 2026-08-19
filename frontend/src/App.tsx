import React, { useState, useRef, useEffect } from 'react';
import { RAGClient } from './api';
import ReactMarkdown from 'react-markdown';
import { FileText, Loader2, Database, Plus, ArrowUp, Building2, Key } from 'lucide-react';

function Section({
  label,
  sub,
  body,
  resolving,
  followUps,
  onFollowUpClick
}: {
  label?: string;
  sub?: string;
  body: string;
  resolving?: boolean;
  followUps?: string[];
  onFollowUpClick?: (text: string) => void;
}) {
  return (
    <div
      className="composer-section"
      style={{
        opacity: resolving ? 0.55 : 1,
        filter: resolving ? "blur(0.5px)" : "blur(0)",
        transform: resolving ? "scale(0.985)" : "scale(1)",
      }}
    >
      {label && (
        <div className="composer-section-header">
          <span className="composer-section-label">{label}</span>
          {sub && <span className="composer-section-sub">{sub}</span>}
        </div>
      )}
      <div className="composer-section-body markdown-body">
        <ReactMarkdown>
          {body || (resolving ? "Synthesizing an answer..." : "")}
        </ReactMarkdown>
      </div>
      {followUps && followUps.length > 0 && !resolving && (
        <div className="follow-up-container">
          <p className="follow-up-title">Suggested Follow-ups:</p>
          <div className="follow-up-pills">
            {followUps.map((q, i) => (
              <button 
                key={i} 
                className="follow-up-pill" 
                onClick={() => onFollowUpClick && onFollowUpClick(q)}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  file?: {name: string, type: string} | null;
  sources?: any[];
  resolving?: boolean;
  followUps?: string[];
  error?: string;
};

function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  
  // Auth state
  const [apiKey, setApiKey] = useState<string>(localStorage.getItem('tenantApiKey') || '');
  const [tenantName, setTenantName] = useState<string>('');
  const [isConfigured, setIsConfigured] = useState<boolean>(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [registerName, setRegisterName] = useState<string>('');
  const [authLoading, setAuthLoading] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [newApiKey, setNewApiKey] = useState<string | null>(null);
  
  const [client, setClient] = useState<RAGClient | null>(null);
  
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<{name: string, type: string} | null>(null);
  
  // ChatComposer state
  const [messages, setMessages] = useState<Message[]>([]);
  const [phase, setPhase] = useState<"idle" | "searching" | "done">("idle");
  const [draft, setDraft] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, phase]);
  
  // Auto login on mount if key exists
  useEffect(() => {
    const savedKey = localStorage.getItem('tenantApiKey');
    if (savedKey && !isConfigured) {
      // Optimistic rendering: Let them into the chat immediately
      setApiKey(savedKey);
      setIsConfigured(true);
      const newClient = new RAGClient(savedKey);
      setClient(newClient);
      
      // Load saved chat history instantly
      const savedMessages = localStorage.getItem(`ragMessages_${savedKey}`);
      if (savedMessages) setMessages(JSON.parse(savedMessages));
      const savedFile = localStorage.getItem(`ragUploadedFile_${savedKey}`);
      if (savedFile) setUploadedFile(JSON.parse(savedFile));
      
      // Verify key and get tenant name in the background
      newClient.getTenantMe().then(tenantInfo => {
        setTenantName(tenantInfo.name);
      }).catch(() => {
        // If the key is actually invalid, log them out
        disconnect();
      });
    }
  }, []);

  const handleLogin = async (key: string) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const newClient = new RAGClient(key);
      const tenantInfo = await newClient.getTenantMe();
      setClient(newClient);
      setTenantName(tenantInfo.name);
      setApiKey(key);
      localStorage.setItem('tenantApiKey', key);
      
      // Load saved chat history
      const savedMessages = localStorage.getItem(`ragMessages_${key}`);
      if (savedMessages) setMessages(JSON.parse(savedMessages));
      const savedFile = localStorage.getItem(`ragUploadedFile_${key}`);
      if (savedFile) setUploadedFile(JSON.parse(savedFile));
      
      setIsConfigured(true);
    } catch (err: any) {
      setAuthError(err.message);
      localStorage.removeItem('tenantApiKey');
      setApiKey('');
    } finally {
      setAuthLoading(false);
    }
  };

  const onLoginFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (apiKey.trim()) {
      handleLogin(apiKey.trim());
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!registerName.trim()) return;
    setAuthLoading(true);
    setAuthError(null);
    try {
      const res = await RAGClient.createTenant(registerName.trim());
      // Show the generated api_key to the user instead of logging in instantly
      setNewApiKey(res.api_key);
    } catch (err: any) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const disconnect = () => {
    localStorage.removeItem('tenantApiKey');
    setApiKey('');
    setTenantName('');
    setIsConfigured(false);
    setClient(null);
    setMessages([]);
    setUploadedFile(null);
  };
  
  // Persist messages and file whenever they change
  useEffect(() => {
    if (apiKey && isConfigured) {
      localStorage.setItem(`ragMessages_${apiKey}`, JSON.stringify(messages));
    }
  }, [messages, apiKey, isConfigured]);

  useEffect(() => {
    if (apiKey && isConfigured) {
      localStorage.setItem(`ragUploadedFile_${apiKey}`, JSON.stringify(uploadedFile));
    }
  }, [uploadedFile, apiKey, isConfigured]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !client) return;

    setIsUploading(true);
    
    try {
      await client.uploadDocument(file);
      setUploadedFile({
        name: file.name,
        type: file.name.split('.').pop()?.toUpperCase() || 'FILE'
      });
      // Reset chat history when a new document is uploaded
      setMessages([]);
      setPhase("idle");
    } catch (err: any) {
      console.error("Upload error:", err);
      // fallback to just clear the upload state on error for simplicity
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const canSend = draft.trim().length > 0 && phase !== "searching";

  const send = async (overrideText?: string) => {
    const userQuery = overrideText || draft.trim();
    if (userQuery.length === 0 || phase === "searching" || !client) return;
    
    const currentFile = uploadedFile;
    const userMsgId = Date.now().toString();
    const assistantMsgId = (Date.now() + 1).toString();
    
    const newUserMsg: Message = {
      id: userMsgId,
      role: "user",
      content: userQuery,
      file: currentFile
    };
    
    const newAssistantMsg: Message = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      resolving: true
    };
    
    setMessages(prev => [...prev, newUserMsg, newAssistantMsg]);
    setUploadedFile(null);
    setDraft("");
    setPhase("searching");

    try {
      await client.generateAnswerStream(
        userQuery, 
        currentFile?.name,
        (text, sources) => {
          let mainText = text;
          let followUps: string[] = [];
          
          const match = text.match(/<FOLLOW_UP>([\s\S]*?)<\/FOLLOW_UP>/);
          if (match) {
            mainText = text.replace(match[0], '').trim();
            const listText = match[1];
            followUps = listText.split('\n')
              .map(line => line.replace(/^-\s*/, '').trim())
              .filter(line => line.length > 0);
          } else if (text.includes('<FOLLOW_UP>')) {
             mainText = text.split('<FOLLOW_UP>')[0].trim();
          }

          setMessages(prev => prev.map(msg => {
            if (msg.id === assistantMsgId) {
              return { ...msg, content: mainText, sources, followUps };
            }
            return msg;
          }));
        }
      );
      
      setMessages(prev => prev.map(msg => {
        if (msg.id === assistantMsgId) {
          return { ...msg, resolving: false };
        }
        return msg;
      }));
      setPhase("done");
    } catch (err: any) {
      setMessages(prev => prev.map(msg => {
        if (msg.id === assistantMsgId) {
          return { ...msg, resolving: false, error: err.message || "An error occurred" };
        }
        return msg;
      }));
      setPhase("done");
    }
  };

  if (!isConfigured) {
    return (
      <div className="modal-overlay">
        <div className="modal-content">
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <Database size={48} strokeWidth={1} style={{ marginBottom: '1rem' }} />
            <h2>{authMode === 'login' ? 'Connect to RAG' : 'Create Organization'}</h2>
            <p className="text-muted" style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
              {authMode === 'login' 
                ? 'Enter your Tenant API Key to continue.'
                : 'Register a new tenant workspace.'}
            </p>
          </div>
          
          {authError && !newApiKey && (
            <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', padding: '0.75rem', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.875rem' }}>
              {authError}
            </div>
          )}

          {newApiKey ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', textAlign: 'center' }}>
              <div style={{ padding: '1rem', background: 'rgba(34, 197, 94, 0.1)', color: '#22c55e', borderRadius: '8px', border: '1px solid rgba(34, 197, 94, 0.2)' }}>
                <p style={{ fontWeight: 600, marginBottom: '0.5rem' }}>Workspace Created Successfully!</p>
                <p style={{ fontSize: '0.875rem' }}>Please copy your Tenant API Key below. Keep it safe, you will not be able to see it again.</p>
              </div>
              
              <div style={{ padding: '1rem', background: 'var(--surface-hover)', borderRadius: '8px', border: '1px solid var(--border-color)', wordBreak: 'break-all', fontFamily: 'monospace', fontSize: '1.1rem', userSelect: 'all' }}>
                {newApiKey}
              </div>
              
              <button 
                type="button" 
                className="btn btn-primary" 
                style={{ width: '100%', marginTop: '0.5rem' }}
                onClick={() => {
                  handleLogin(newApiKey);
                  setNewApiKey(null);
                }}
              >
                Continue to Workspace
              </button>
            </div>
          ) : authMode === 'login' ? (
            <form onSubmit={onLoginFormSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', background: 'var(--surface-hover)', borderRadius: '8px', padding: '0 1rem', border: '1px solid var(--border-color)' }}>
                <Key size={18} className="text-muted" />
                <input
                  type="password"
                  placeholder="Tenant API Key"
                  className="input-field"
                  style={{ border: 'none', background: 'transparent', boxShadow: 'none' }}
                  value={apiKey}
                  onChange={e => setApiKey(e.target.value)}
                  autoFocus
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={authLoading}>
                {authLoading ? <Loader2 size={18} className="animate-pulse" /> : 'Connect'}
              </button>
              <button type="button" className="btn btn-outline" onClick={() => { setAuthMode('register'); setAuthError(null); }} style={{ width: '100%', fontSize: '0.8rem' }}>
                Need a workspace? Create one
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', background: 'var(--surface-hover)', borderRadius: '8px', padding: '0 1rem', border: '1px solid var(--border-color)' }}>
                <Building2 size={18} className="text-muted" />
                <input
                  type="text"
                  placeholder="Organization Name"
                  className="input-field"
                  style={{ border: 'none', background: 'transparent', boxShadow: 'none' }}
                  value={registerName}
                  onChange={e => setRegisterName(e.target.value)}
                  autoFocus
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={authLoading}>
                {authLoading ? <Loader2 size={18} className="animate-pulse" /> : 'Register Tenant'}
              </button>
              <button type="button" className="btn btn-outline" onClick={() => { setAuthMode('login'); setAuthError(null); }} style={{ width: '100%', fontSize: '0.8rem' }}>
                Already have a key? Log in
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={`app-container ${theme === 'light' ? 'theme-light' : ''}`}>
      <header className="app-header">
        <div className="logo-text">
          {/* Removed logo and naming per request */}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button 
            className="btn btn-outline" 
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            title="Toggle Theme"
          >
            {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--surface-hover)', padding: '0.25rem 0.75rem', borderRadius: '16px' }}>
            <Building2 size={16} className="text-muted" />
            <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>{tenantName || 'Tenant'}</span>
          </div>
          <button className="btn btn-outline" onClick={disconnect}>
            Disconnect
          </button>
        </div>
      </header>

      <main className="main-content">
        
        <div className="chat-composer">
          {/* conversation — fixed region */}
          <div className="composer-body">
            {phase === "idle" && messages.length === 0 && (
              <div style={{ textAlign: 'center', opacity: 0.5, marginTop: '20vh' }}>
                <Database size={48} strokeWidth={1} style={{ margin: '0 auto 1rem' }} />
                <h2>What can I help with?</h2>
              </div>
            )}

            {messages.map((msg) => {
              if (msg.role === "user") {
                return (
                  <div key={msg.id} className="composer-user-bubble-wrapper" style={{ flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
                    {msg.file && (
                      <div className="uploaded-file-pill" style={{ alignSelf: 'flex-end', margin: 0, backgroundColor: 'var(--surface-hover)', borderColor: 'var(--border-color)' }}>
                        <div className="uploaded-file-icon">
                          <FileText size={20} strokeWidth={2} />
                        </div>
                        <div className="uploaded-file-info">
                          <span className="uploaded-file-name">{msg.file.name}</span>
                          <span className="uploaded-file-type">{msg.file.type}</span>
                        </div>
                      </div>
                    )}
                    <div className="composer-user-bubble">
                      {msg.content}
                    </div>
                  </div>
                );
              } else {
                return (
                  <Section
                    key={msg.id}
                    label={msg.resolving ? "Searching Knowledge Base..." : undefined}
                    sub={msg.resolving ? "Retrieval & Generation" : undefined}
                    body={msg.error ? `**Error**: ${msg.error}` : msg.content}
                    resolving={msg.resolving}
                    followUps={msg.followUps}
                    onFollowUpClick={(q) => send(q)}
                  />
                );
              }
            })}
            <div ref={bottomRef} />
          </div>

          {/* composer footer (input area) */}
          <div className="composer-footer">
            <div
              className="composer-input-wrapper"
              onClick={() => inputRef.current?.focus()}
            >
              {uploadedFile && (
                <div className="uploaded-file-pill">
                  <div className="uploaded-file-icon">
                    <FileText size={20} strokeWidth={2} />
                  </div>
                  <div className="uploaded-file-info">
                    <span className="uploaded-file-name">{uploadedFile.name}</span>
                    <span className="uploaded-file-type">{uploadedFile.type}</span>
                  </div>
                </div>
              )}

              <div className="composer-input-row">
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  style={{ display: 'none' }} 
                  accept=".pdf,.txt"
                  onChange={handleFileUpload}
                />
                
                <button
                  type="button"
                  aria-label="Upload document"
                  className="composer-btn-add"
                  disabled={isUploading}
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                >
                  {isUploading ? (
                    <Loader2 size={20} className="animate-pulse" />
                  ) : (
                    <Plus size={24} />
                  )}
                </button>

                <textarea
                  ref={inputRef}
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      send();
                    }
                  }}
                  placeholder="Ask a question about your knowledge base..."
                  aria-label="Chat prompt"
                  className="composer-input"
                  rows={1}
                />
                
                <div className="composer-input-actions">
                  <button
                    type="button"
                    aria-label="Send"
                    disabled={!canSend}
                    onClick={(e) => {
                      e.stopPropagation();
                      send();
                    }}
                    className="composer-btn-send"
                    style={{
                      background: canSend ? "var(--ink)" : "var(--line-strong)",
                      color: canSend ? "var(--surface)" : "var(--ink-2)",
                      borderRadius: "50%",
                      width: "32px",
                      height: "32px",
                    }}
                  >
                    <ArrowUp size={18} strokeWidth={2.5} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;


// Cache buster 2
