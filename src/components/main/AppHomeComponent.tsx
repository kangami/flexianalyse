import React, { useState, useRef, useEffect } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';
import { useAuth } from '../auth/AuthProvider';
import { useTheme } from '../../contexts/ThemeContext';
import { authFetch } from '../../lib/apiClient';
import { DB_ENGINES, DbEngineLogo } from '../../lib/dbEngines';
import DbResultGrid from './DbResultGrid';
import DbChatPanel, { DbTurn } from './DbChatPanel';
import ScopeSelector, { ScopeConnector } from './ScopeSelector';

interface AppHomeComponentProps {
    onQuerySubmit: (query: string, mode: 'online' | 'local') => void;
    loading: boolean;
    selectedModel: string;
    setSelectedModel: (model: string) => void;
    researchMode: 'online' | 'local';
    setResearchMode: React.Dispatch<React.SetStateAction<'online' | 'local'>>;
    language?: 'en' | 'fr' | 'es';
}

const AppHomeComponent: React.FC<AppHomeComponentProps> = ({
    loading,
    researchMode,
    setResearchMode,
}) => {
    const { t } = useLanguage();
    const { account } = useAuth();
    const { theme } = useTheme();

    const tc = {
        pageBg:         theme === 'dark'       ? { background: 'linear-gradient(135deg,#111827,#1f2937,#111827)' }
                      : theme === 'dark-blue'  ? { background: 'linear-gradient(135deg,#0f172a,#1e3a8a,#0f172a)' }
                      :                         { background: 'linear-gradient(135deg,#f8fafc,#ffffff,#eff6ff)' },
        formBg:         theme === 'dark'       ? 'rgba(31,41,55,0.95)'
                      : theme === 'dark-blue'  ? 'rgba(15,23,42,0.85)'
                      :                         'rgba(255,255,255,0.7)',
        formBorder:     theme === 'dark'       ? '#374151'
                      : theme === 'dark-blue'  ? '#1e40af'
                      :                         'rgba(209,213,219,0.8)',
        ctrlBg:         theme === 'dark'       ? 'rgba(55,65,81,0.7)'
                      : theme === 'dark-blue'  ? 'rgba(30,58,138,0.5)'
                      :                         'rgba(249,250,251,0.6)',
        ctrlBorder:     theme === 'dark'       ? '#374151'
                      : theme === 'dark-blue'  ? '#1e40af'
                      :                         '#f3f4f6',
        textPrimary:    theme !== 'white'      ? '#f3f4f6' : '#374151',
        textMuted:      theme === 'dark'       ? '#9ca3af'
                      : theme === 'dark-blue'  ? '#93c5fd'
                      :                         '#6b7280',
        modelBtn:       theme === 'dark'       ? { background:'#374151', color:'#f3f4f6', borderColor:'#4b5563' }
                      : theme === 'dark-blue'  ? { background:'#1e3a8a', color:'#e0e7ff', borderColor:'#1e40af' }
                      :                         { background:'#ffffff',  color:'#374151', borderColor:'#e5e7eb' },
        modeOnline:     theme === 'dark'       ? { background:'#1d3353', color:'#93c5fd', borderColor:'#374151' }
                      : theme === 'dark-blue'  ? { background:'#1e3a8a', color:'#bfdbfe', borderColor:'#1e40af' }
                      :                         { background:'#dbeafe',  color:'#1d4ed8', borderColor:'#e5e7eb' },
        modeLocal:      theme === 'dark'       ? { background:'#374151', color:'#f3f4f6', borderColor:'#4b5563' }
                      : theme === 'dark-blue'  ? { background:'#0f172a', color:'#e0e7ff', borderColor:'#1e40af' }
                      :                         { background:'#ffffff',  color:'#374151', borderColor:'#e5e7eb' },
        connBtn:        theme === 'dark'       ? { background:'#374151', borderColor:'#4b5563' }
                      : theme === 'dark-blue'  ? { background:'#1e3a8a', borderColor:'#1e40af' }
                      :                         { background:'rgba(255,255,255,0.8)', borderColor:'#e5e7eb' },
        modalBg:        theme === 'dark'       ? '#1f2937'
                      : theme === 'dark-blue'  ? '#0f172a'
                      :                         '#ffffff',
        modalBorder:    theme === 'dark'       ? '#374151'
                      : theme === 'dark-blue'  ? '#1e40af'
                      :                         '#e5e7eb',
        modalLabel:     theme === 'dark'       ? '#9ca3af'
                      : theme === 'dark-blue'  ? '#93c5fd'
                      :                         '#6b7280',
        inputBg:        theme === 'dark'       ? '#374151'
                      : theme === 'dark-blue'  ? '#1e3a8a'
                      :                         '#ffffff',
        inputBorder:    theme === 'dark'       ? '#4b5563'
                      : theme === 'dark-blue'  ? '#1e40af'
                      :                         '#e5e7eb',
        cancelBtn:      theme === 'dark'       ? { background:'#374151', color:'#d1d5db', borderColor:'#4b5563' }
                      : theme === 'dark-blue'  ? { background:'#1e3a8a', color:'#93c5fd', borderColor:'#1e40af' }
                      :                         { background:'#ffffff',  color:'#4b5563', borderColor:'#e5e7eb' },
    };
    const [query, setQuery] = useState<string>('');
    const [isMobile, setIsMobile] = useState(false);
    const [alertMessage, setAlertMessage] = useState<string>('');
    const [currentFeature, setCurrentFeature] = useState(0);
    const [activeConnector, setActiveConnector] = useState<string | null>(null);
    const [connectorForm, setConnectorForm] = useState<Record<string, string>>({});
    const [connectorSaving, setConnectorSaving] = useState(false);
    const [connectorMsg, setConnectorMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const [enterpriseLoading, setEnterpriseLoading] = useState(false);
    // Multi-turn discussion (in-memory) + the latest result set shown in the grid.
    const [conversation, setConversation] = useState<DbTurn[]>([]);
    const [pendingQuery, setPendingQuery]   = useState<string | null>(null);
    const [tableColumns, setTableColumns]   = useState<string[]>([]);
    const [tableRows, setTableRows]         = useState<Record<string, unknown>[]>([]);
    const [tableSql, setTableSql]           = useState<string>('');

    // Connectors of the org — feed the perimeter selector and the engine badges.
    const [connectors, setConnectors]       = useState<ScopeConnector[]>([]);
    const [searchScope, setSearchScope]     = useState<string | null>(null); // null = all context

    useEffect(() => {
        const headers: Record<string, string> = {};
        if (account?.organization_id) headers['X-Organization-Id'] = account.organization_id;
        authFetch(`${API_BASE}/api/v2/connectors`, { headers })
            .then(r => r.json())
            .then(d => setConnectors(Array.isArray(d.data) ? d.data : []))
            .catch(() => {});
    }, [account?.organization_id]);

    // Number of connectors per engine (for the notification-style badges).
    const engineCounts: Record<string, number> = {};
    for (const c of connectors) if (c.engine) engineCounts[c.engine] = (engineCounts[c.engine] || 0) + 1;

    // Search runs across every connector of the user's first (default)
    // organisation — resolved from the auth context, no manual org selection.
    const runSearch = async (q: string) => {
        const question = q.trim();
        if (!question || enterpriseLoading) return;
        setEnterpriseLoading(true);
        setPendingQuery(question);
        setQuery('');
        try {
            const headers: Record<string, string> = { 'Content-Type': 'application/json' };
            // Explicit when known; otherwise the backend defaults to the user's
            // first membership org (validated against their memberships).
            if (account?.organization_id) headers['X-Organization-Id'] = account.organization_id;
            const res = await authFetch(`${API_BASE}/api/mcp/search`, {
                method: 'POST',
                headers,
                // connector_id scopes the live SQL to one database; null = all context.
                body: JSON.stringify({ query: question, connector_id: searchScope }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || res.statusText);
            const sources: DbTurn['sources'] = Array.isArray(data.sources) ? data.sources : [];
            const columns: string[] = Array.isArray(data.sql_columns) ? data.sql_columns : [];
            const rows: Record<string, unknown>[] = Array.isArray(data.sql_rows) ? data.sql_rows : [];
            setConversation(prev => [...prev, {
                id: `${Date.now()}`,
                query: question,
                answer: data.answer || '',
                sql: data.generated_sql || '',
                sqlError: data.sql_error || null,
                sources,
            }]);
            // Refresh the left grid only when this turn actually returned a table.
            if (columns.length) {
                setTableColumns(columns);
                setTableRows(rows);
                setTableSql(data.generated_sql || '');
            }
        } catch (e: unknown) {
            setConversation(prev => [...prev, {
                id: `${Date.now()}`,
                query: question,
                answer: `⚠️ Search failed: ${(e as Error).message}`,
                sources: [],
            }]);
        } finally {
            setPendingQuery(null);
            setEnterpriseLoading(false);
        }
    };

    const handleEnterpriseSearch = () => runSearch(query);

    const resetSearch = () => {
        setConversation([]);
        setPendingQuery(null);
        setTableColumns([]);
        setTableRows([]);
        setTableSql('');
        setQuery('');
    };

    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-dismiss alert after 5 seconds
    useEffect(() => {
        if (alertMessage) {
            const timer = setTimeout(() => {
                setAlertMessage('');
            }, 5000);
            return () => clearTimeout(timer);
        }
    }, [alertMessage]);

    // Mobile detection
    useEffect(() => {
        const checkIfMobile = () => {
            setIsMobile(window.innerWidth < 768);
        };

        checkIfMobile();
        window.addEventListener('resize', checkIfMobile);
        return () => window.removeEventListener('resize', checkIfMobile);
    }, []);

    // Auto-resize textarea based on content
    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = `${Math.min(textarea.scrollHeight, isMobile ? 100 : 150)}px`;
        }
    }, [query, isMobile]);

    // Animated features rotation
    useEffect(() => {
        const features = [
            t('app.feature1'),
            t('app.feature2'),
            t('app.feature3'),
            t('app.feature4')
        ];

        let currentIndex = 0;
        const interval = setInterval(() => {
            currentIndex = (currentIndex + 1) % features.length;
            setCurrentFeature(currentIndex);
        }, 3000);

        return () => clearInterval(interval);
    }, []);

    const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000';

    // Database engines only (FlexiAnalyse is a database agent). Each exposes
    // DBeaver-style connection fields (host/port/database/user/password); the
    // backend assembles the URL. Shared with the Sidebar via ../../lib/dbEngines.
    const CONNECTOR_DEFS = DB_ENGINES.map(e => ({
        id: e.id,
        label: e.title,
        fields: [
            { key: 'name', label: t('connector.fields.name'), placeholder: `My ${e.title}` },
            ...e.fields,
        ],
        icon: <DbEngineLogo engine={e.id} size={20} />,
    }));

    const handleSaveConnector = async () => {
        const engine = DB_ENGINES.find(e => e.id === activeConnector);
        const def = CONNECTOR_DEFS.find(d => d.id === activeConnector);
        if (!engine || !def) return;
        setConnectorSaving(true);
        setConnectorMsg(null);
        try {
            const connection: Record<string, string> = {};
            engine.fields.forEach(f => { if (connectorForm[f.key]) connection[f.key] = connectorForm[f.key]; });
            if (!connection.host) throw new Error('Host is required');
            const dbKey = engine.id === 'oracle' ? 'service_name' : 'database';
            if (!connection[dbKey]) throw new Error(engine.id === 'oracle' ? 'Service name is required' : 'Database is required');

            const body = {
                type: 'sql',
                engine: engine.id,
                name: connectorForm.name || t('connector.newConnectionName', { service: def.label }),
                connection,
            };
            const r = await authFetch(`${API_BASE}/api/v2/connectors`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (!r.ok) throw new Error((await r.json())?.error || r.statusText);
            await r.json();
            setConnectorMsg({ text: t('connector.addedSuccessfully'), ok: true });
            setTimeout(() => { setActiveConnector(null); setConnectorForm({}); setConnectorMsg(null); }, 2000);
        } catch (e: unknown) {
            const errorMessage = (e as Error).message || String(e);
            setConnectorMsg({ text: t('connector.error', { message: errorMessage }), ok: false });
        } finally {
            setConnectorSaving(false);
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim() || enterpriseLoading) return;
        // The search always runs across the org's connectors (Text-to-SQL +
        // ingested content). No more Enterprise toggle / manual org selection.
        handleEnterpriseSearch();
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    const closeModal = () => { setActiveConnector(null); setConnectorForm({}); setConnectorMsg(null); };

    const activeDef = CONNECTOR_DEFS.find(d => d.id === activeConnector) ?? null;

    // Once a search is submitted, swap the centered hero for the two-pane view:
    // DBeaver-style result grid on the LEFT, running discussion on the RIGHT.
    if (conversation.length > 0 || enterpriseLoading) {
        return (
            <div className="h-full w-full flex overflow-hidden">
                {/* LEFT: DBeaver-style grid — desktop only (needs width) */}
                <div className="hidden md:block flex-1 min-w-0 border-r border-gray-200 h-full">
                    <DbResultGrid
                        columns={tableColumns}
                        rows={tableRows}
                        sql={tableSql}
                        loading={enterpriseLoading && tableColumns.length === 0}
                    />
                </div>
                {/* RIGHT: conversation — always visible, full width on mobile */}
                <div className="w-full md:w-[440px] flex-shrink-0 h-full">
                    <DbChatPanel
                        turns={conversation}
                        pendingQuery={pendingQuery}
                        loading={enterpriseLoading}
                        onSubmit={runSearch}
                        onNewSearch={resetSearch}
                        connectors={connectors}
                        scope={searchScope}
                        onScopeChange={setSearchScope}
                    />
                </div>
            </div>
        );
    }

    return (
        <div className="h-full w-full flex flex-col overflow-y-auto" style={tc.pageBg}>

            {/* ─── Connector Modal ─── */}
            {activeDef && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={closeModal}>
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
                    <div
                        className="relative rounded-2xl shadow-2xl w-full max-w-md p-6 animate-scaleIn"
                        style={{ background: tc.modalBg, border: `1px solid ${tc.modalBorder}` }}
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between mb-5">
                            <div className="flex items-center gap-3 min-w-0">
                                <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: tc.inputBg, border: `1px solid ${tc.modalBorder}` }}>
                                    {activeDef.icon}
                                </div>
                                <div className="min-w-0">
                                    <p className="text-[10px] uppercase tracking-wider font-medium break-words" style={{ color: tc.textMuted }}>{t('connector.newConnection')}</p>
                                    <p className="text-base font-bold break-words" style={{ color: tc.textPrimary }}>{activeDef.label}</p>
                                </div>
                            </div>
                            <button onClick={closeModal} className="w-8 h-8 flex items-center justify-center rounded-full transition-colors text-lg" style={{ color: tc.textMuted }} aria-label={t('app.close')}>✕</button>
                        </div>

                        {/* Fields */}
                        <div className="flex flex-col gap-3 mb-4">
                            {activeDef.fields.map(field => (
                                <div key={field.key}>
                                    <label className="block text-[11px] mb-1.5 font-semibold uppercase tracking-wider" style={{ color: tc.modalLabel }}>{field.label}</label>
                                    <input
                                        type={(field as { type?: string }).type || 'text'}
                                        placeholder={field.placeholder}
                                        value={connectorForm[field.key] || ''}
                                        onChange={e => setConnectorForm(f => ({ ...f, [field.key]: e.target.value }))}
                                        className="w-full text-sm rounded-xl px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-purple-200/60 transition-all"
                                        style={{ background: tc.inputBg, borderColor: tc.inputBorder, color: tc.textPrimary, border: `1px solid ${tc.inputBorder}` }}
                                    />
                                </div>
                            ))}
                        </div>

                        {/* Message */}
                        {connectorMsg && (
                            <p className={`mb-3 text-xs font-medium px-1 ${connectorMsg.ok ? 'text-green-600' : 'text-red-500'}`}>
                                {connectorMsg.text}
                            </p>
                        )}

                        {/* Actions */}
                        <div className="flex gap-2">
                            <button onClick={closeModal} className="flex-1 text-sm px-4 py-2.5 rounded-xl transition-colors font-medium" style={tc.cancelBtn}>
                                {t('connector.cancel')}
                            </button>
                            <button
                                onClick={handleSaveConnector}
                                disabled={connectorSaving}
                                className="flex-1 text-sm px-4 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 font-semibold transition-all flex items-center justify-center gap-2 shadow-md shadow-purple-200"
                            >
                                {connectorSaving ? (
                                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"/>
                                        <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" className="opacity-75"/>
                                    </svg>
                                ) : (
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                                    </svg>
                                )}
                                {connectorSaving ? t('connector.connecting') : t('connector.saveConnection')}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* ─── Centered main content ─── */}
            <div className="flex-1 flex flex-col items-center justify-center px-4 py-10 min-h-0">
                <div className="w-full max-w-2xl">
                    {/* Flexi Logo with Animated Features */}
                    <div className="mb-8 text-center">
                        {/* Row 1: Logo + Flexi */}
                        <div className="flex items-center justify-center gap-2 mb-1">
                            <img
                                src="/flexiAnalyseLogo_website.png"
                                alt={t('app.logoAlt')}
                                className="h-9 w-auto flex-shrink-0"
                            />
                            <h1 className="text-3xl font-extrabold text-purple-600 shadow-text-preset flex-shrink-0 m-0 tracking-tight">Flexi</h1>
                        </div>

                        {/* Row 2: Rotating "can ..." — same size, centered, gradient */}
                        <div className="min-h-[2.5rem] flex items-center justify-center py-1">
                            {currentFeature === 0 && (
                                <span
                                    className="animate-fade-in-out text-xl sm:text-3xl font-extrabold tracking-tight text-center leading-tight"
                                    style={{ background: 'linear-gradient(90deg,#f59e0b,#f97316)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}
                                >
                                    {t('app.feature1')}
                                </span>
                            )}
                            {currentFeature === 1 && (
                                <span
                                    className="animate-fade-in-out text-xl sm:text-3xl font-extrabold tracking-tight text-center leading-tight"
                                    style={{ background: 'linear-gradient(90deg,#8b5cf6,#ec4899)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}
                                >
                                    {t('app.feature2')}
                                </span>
                            )}
                            {currentFeature === 2 && (
                                <span
                                    className="animate-fade-in-out text-xl sm:text-3xl font-extrabold tracking-tight text-center leading-tight"
                                    style={{ background: 'linear-gradient(90deg,#3b82f6,#06b6d4)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}
                                >
                                    {t('app.feature3')}
                                </span>
                            )}
                            {currentFeature === 3 && (
                                <span
                                    className="animate-fade-in-out text-xl sm:text-3xl font-extrabold tracking-tight text-center leading-tight"
                                    style={{ background: 'linear-gradient(90deg,#10b981,#3b82f6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}
                                >
                                    {t('app.feature4')}
                                </span>
                            )}
                        </div>
                    </div>

                    {/* Alert for limitations */}
                    {alertMessage && (
                        <div className="mb-4 bg-yellow-500 text-white px-4 py-3 rounded-lg shadow-lg animate-slide-in-right">
                            <div className="flex items-start justify-between gap-3">
                                <div className="flex items-start gap-2 flex-1">
                                    <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                    </svg>
                            <p className="text-sm font-medium">{alertMessage}</p>
                                </div>
                                <button
                                    onClick={() => setAlertMessage('')}
                                    className="text-white hover:text-gray-200 transition-colors flex-shrink-0"
                                    aria-label={t('app.closeAlert')}
                                >
                                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                                    </svg>
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Integrated textarea with controls - Modern Stylish Design */}
                    <div className="group relative mx-auto w-full max-w-2xl rounded-2xl backdrop-blur-xl shadow-[0_2px_12px_-2px_rgba(0,0,0,0.12)] overflow-hidden transition-all duration-300 border"
                         style={{ background: tc.formBg, borderColor: tc.formBorder }}>
                        {/* Subtle gradient accent on top */}
                        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-blue-400/50 to-transparent" />

                        {/* Textarea with reduced height and modern styling */}
                        <textarea
                            ref={textareaRef}
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={t('query.placeholder')}
                            className={`
                                w-full bg-transparent outline-none
                                resize-none overflow-y-auto whitespace-pre-wrap
                                scrollbar-thin scrollbar-track-transparent
                                px-4 pt-3.5 pb-2
                                ${isMobile ? 'min-h-[48px] text-sm' : 'min-h-[64px] text-[15px]'}
                                leading-relaxed transition-all duration-150
                            `}
                            disabled={loading}
                            rows={isMobile ? 2 : 3}
                            style={{ fontSize: isMobile ? '14px' : '15px', color: tc.textPrimary }}
                            aria-label={t('query.inputLabel')}
                        />

                        {/* Controls bar inside the textarea container */}
                        <div className="border-t px-3 py-2 flex flex-wrap items-center justify-between gap-2" style={{ background: tc.ctrlBg, borderColor: tc.ctrlBorder }}>
                            {/* Left controls */}
                            <div className="flex flex-wrap gap-2">
                                {/* Search perimeter — which database (or all context) to search */}
                                <ScopeSelector
                                    connectors={connectors}
                                    value={searchScope}
                                    onChange={setSearchScope}
                                />

                                {/* Research mode toggle */}
                    <button
                        onClick={() => setResearchMode(researchMode === 'online' ? 'local' : 'online')}
                        className="rounded-md px-2 py-1 text-xs flex items-center gap-1 transition-colors border"
                        style={researchMode === 'online' ? tc.modeOnline : tc.modeLocal}
                        aria-label={t('query.toggleMode')}
                    >
                                    {researchMode === 'online' ? (
                                        <>
                                            <svg
                                                xmlns="http://www.w3.org/2000/svg"
                                                viewBox="0 0 20 20"
                                                fill="currentColor"
                                                className="w-3 h-3"
                                            >
                                                <path fillRule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clipRule="evenodd" />
                                            </svg>
                                            {t('query.research')}
                                        </>
                                    ) : (
                                        <>
                                            <svg
                                                xmlns="http://www.w3.org/2000/svg"
                                                viewBox="0 0 20 20"
                                                fill="currentColor"
                                                className="w-3 h-3"
                                            >
                                                <path fillRule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5z" clipRule="evenodd" />
                                            </svg>
                                            {t('query.local')}
                                        </>
                                    )}
                                </button>
                            </div>

                            {/* Submit button */}
                    <button
                        onClick={handleSubmit}
                        disabled={loading || enterpriseLoading || !query.trim()}
                        className={`
                            rounded-xl p-2
                            ${loading || enterpriseLoading || !query.trim()
                                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                : 'bg-gradient-to-br from-blue-500 via-blue-600 to-indigo-600 hover:shadow-lg hover:shadow-blue-500/30 active:scale-90 text-white'
                            }
                            transition-all duration-200 border border-transparent
                        `}
                        aria-label={t('query.submit')}
                    >
                                {(loading || enterpriseLoading) ? (
                                    <svg
                                        className="animate-spin h-4 w-4"
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                    >
                                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"/>
                                        <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" className="opacity-75"/>
                                    </svg>
                                ) : (
                                    <svg
                                        className="h-4 w-4"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
                                    </svg>
                                )}
                            </button>
                        </div>

                    </div>

                    {/* ─── Connector icon strip (below form) ─── */}
                    <div className="mt-3 flex items-center justify-center flex-wrap gap-2">
                        {CONNECTOR_DEFS.map(({ id, label, icon }) => {
                            const count = engineCounts[id] || 0;
                            return (
                            <button
                                key={id}
                                title={count > 0 ? `${count} ${label} connector${count === 1 ? '' : 's'}` : t('connector.connectService', { service: label })}
                                onClick={() => { setActiveConnector(id); setConnectorForm({}); setConnectorMsg(null); }}
                                className="relative flex items-center gap-1.5 px-2.5 py-1.5 rounded-full border hover:border-purple-400 hover:scale-105 hover:shadow-sm transition-all duration-200"
                                style={tc.connBtn}
                                aria-label={t('connector.connect', { service: label })}
                            >
                                <span className="w-4 h-4 flex-shrink-0 flex items-center justify-center">{icon}</span>
                                <span className="text-xs font-medium whitespace-nowrap" style={{ color: tc.textMuted }}>{label}</span>
                                {count > 0 && (
                                    <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 px-1 flex items-center justify-center rounded-full bg-purple-600 text-white text-[9px] font-bold tabular-nums shadow">
                                        {count}
                                    </span>
                                )}
                            </button>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AppHomeComponent;