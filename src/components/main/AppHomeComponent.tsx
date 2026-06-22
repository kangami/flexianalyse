import React, { useState, useRef, useEffect } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';
import { useAuth } from '../auth/AuthProvider';
import { useTheme } from '../../contexts/ThemeContext';

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
    onQuerySubmit,
    loading,
    selectedModel,
    setSelectedModel,
    researchMode,
    setResearchMode,
    language = 'en'
}) => {
    const { t } = useLanguage();
    const { isAuthenticated } = useAuth();
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
    const [isModelPopupOpen, setIsModelPopupOpen] = useState(false);
    const [currentFeature, setCurrentFeature] = useState(0);
    const [activeConnector, setActiveConnector] = useState<string | null>(null);
    const [connectorForm, setConnectorForm] = useState<Record<string, string>>({});
    const [connectorSaving, setConnectorSaving] = useState(false);
    const [connectorMsg, setConnectorMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const modelPopupRef = useRef<HTMLDivElement>(null);
    const modelBadgeRef = useRef<HTMLDivElement>(null);

    // Close model popup on outside click
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (
                modelPopupRef.current && !modelPopupRef.current.contains(e.target as Node) &&
                modelBadgeRef.current && !modelBadgeRef.current.contains(e.target as Node)
            ) {
                setIsModelPopupOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Auto-dismiss alert after 5 seconds
    useEffect(() => {
        if (alertMessage) {
            const timer = setTimeout(() => {
                setAlertMessage('');
            }, 5000);
            return () => clearTimeout(timer);
        }
    }, [alertMessage]);

    // Check query limit for unauthenticated users
    const checkQueryLimit = (): boolean => {
        if (isAuthenticated) return true;

        const today = new Date().toDateString();
        const stored = localStorage.getItem('daily_queries');
        if (!stored) return true;

        try {
            const data = JSON.parse(stored);
            if (data.date === today) {
                return (data.count || 0) < 5;
            }
        } catch (e) {
            console.error(t('app.errors.dailyQueries'), e);
        }
        return true;
    };

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

    const CONNECTOR_DEFS = [
        {
            id: 'google_drive', label: 'Google Drive', oauth: true,
            fields: [
                { key: 'name', label: t('connector.fields.name'), placeholder: t('connector.placeholders.myGoogleDrive') },
                { key: 'folder_id', label: t('connector.fields.folderId'), placeholder: t('connector.placeholders.folderId') },
            ],
            icon: (
                <svg viewBox="0 0 87.3 78" className="w-5 h-5">
                    <path d="M6.6 66.85l3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8H0c0 1.55.4 3.1 1.2 4.5l5.4 9.35z" fill="#0066DA"/>
                    <path d="M43.65 25L29.9 1.2c-1.35.8-2.5 1.9-3.3 3.3L1.2 52.5c-.8 1.4-1.2 2.95-1.2 4.5h27.5L43.65 25z" fill="#00AC47"/>
                    <path d="M73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5H59.85l6.1 10.6 7.6 13.2z" fill="#EA4335"/>
                    <path d="M43.65 25L57.4 1.2C56.05.4 54.5 0 52.9 0H34.4c-1.6 0-3.15.45-4.5 1.2L43.65 25z" fill="#00832D"/>
                    <path d="M59.85 57H27.5l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2L59.85 57z" fill="#2684FC"/>
                    <path d="M73.4 26.5l-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3L43.65 25l16.2 32h27.5c0-1.55-.4-3.1-1.2-4.5L73.4 26.5z" fill="#FFBA00"/>
                </svg>
            ),
        },
        {
            id: 'dropbox', label: 'Dropbox', oauth: true,
            fields: [
                { key: 'name', label: t('connector.fields.name'), placeholder: t('connector.placeholders.myDropbox') },
            ],
            icon: (
                <svg viewBox="0 0 43 40" className="w-5 h-5">
                    <path d="M12.6 0L0 8.1l8.9 7.1 12.6-7.8L12.6 0zM0 22.3l12.6 8.1 8.9-7.4-12.6-7.8L0 22.3zm21.5.7l8.9 7.4 12.6-8.1-8.9-7.1-12.6 7.8zm21.5-14.9L30.4 0l-8.9 7.4 12.6 7.8 8.9-7.1zM12.7 32.4l8.8 7.4 8.9-7.4-8.9-7.1-8.8 7.1z" fill="#0061FF"/>
                </svg>
            ),
        },
        {
            id: 'sharepoint', label: 'SharePoint', oauth: true,
            fields: [
                { key: 'name', label: t('connector.fields.name'), placeholder: t('connector.placeholders.mySharePoint') },
                { key: 'tenant_id', label: t('connector.fields.tenantId'), placeholder: t('connector.placeholders.tenantId') },
                { key: 'site_url', label: t('connector.fields.siteUrl'), placeholder: t('connector.placeholders.siteUrl') },
            ],
            icon: (
                <svg viewBox="0 0 32 32" className="w-5 h-5">
                    <circle cx="18" cy="11" r="9" fill="#036C70"/>
                    <circle cx="13" cy="20" r="7" fill="#1A9BA1"/>
                    <circle cx="20" cy="23" r="5.5" fill="#37C6D0"/>
                </svg>
            ),
        },
        {
            id: 'database', label: 'SQL Database', oauth: false,
            fields: [
                { key: 'name', label: t('connector.fields.name'), placeholder: t('connector.placeholders.myDatabase') },
                { key: 'connection_url', label: t('connector.fields.connectionUrl'), placeholder: t('connector.placeholders.connectionUrl') },
            ],
            icon: (
                <svg viewBox="0 0 32 32" className="w-5 h-5">
                    <ellipse cx="16" cy="8" rx="12" ry="5" fill="#E48E00"/>
                    <path d="M4 8v16c0 2.76 5.37 5 12 5s12-2.24 12-5V8c0 2.76-5.37 5-12 5S4 10.76 4 8z" fill="#FFC107"/>
                </svg>
            ),
        },
    ] as const;

    const handleSaveConnector = async () => {
        const def = CONNECTOR_DEFS.find(d => d.id === activeConnector);
        if (!def) return;
        setConnectorSaving(true);
        setConnectorMsg(null);
        try {
            const body: Record<string, string | undefined> = {
                type: def.id === 'database' ? 'sql' : def.id,
                name: connectorForm.name || t('connector.newConnectionName', { service: def.label }),
            };
            if (def.id === 'database') {
                if (!connectorForm.connection_url) throw new Error(t('connector.errors.connectionUrlRequired'));
                body.token = connectorForm.connection_url;
            } else if (def.id === 'sharepoint') {
                if (!connectorForm.tenant_id) throw new Error(t('connector.errors.tenantIdRequired'));
                if (!connectorForm.site_url) throw new Error(t('connector.errors.siteUrlRequired'));
                body.token = JSON.stringify({ tenant_id: connectorForm.tenant_id, site_url: connectorForm.site_url });
            } else if (def.id === 'google_drive') {
                body.token = connectorForm.folder_id || undefined;
            }
            const r = await fetch(`${API_BASE}/api/v2/connectors`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (!r.ok) throw new Error((await r.json())?.error || r.statusText);
            const saved = await r.json();
            if (def.oauth) {
                setConnectorMsg({ text: t('connector.savedOpening', { service: def.label }), ok: true });
                setTimeout(() => window.open(`${API_BASE}/auth/${def.id}?connector_id=${saved.id}`, '_blank'), 400);
            } else {
                setConnectorMsg({ text: t('connector.addedSuccessfully'), ok: true });
                setTimeout(() => { setActiveConnector(null); setConnectorForm({}); setConnectorMsg(null); }, 2000);
            }
        } catch (e: unknown) {
            const errorMessage = (e as Error).message || String(e);
            setConnectorMsg({ text: t('connector.error', { message: errorMessage }), ok: false });
        } finally {
            setConnectorSaving(false);
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (query.trim() && !loading) {
            // Check query limit for unauthenticated users
            if (!isAuthenticated && !checkQueryLimit()) {
                setAlertMessage(t('query.limitReached'));
                return;
            }
            onQuerySubmit(query, researchMode);
            setQuery('');
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            // Check limit before submitting
            if (query.trim() && !loading) {
                if (!isAuthenticated && !checkQueryLimit()) {
                    setAlertMessage(t('query.limitReached'));
                    return;
                }
            }
            handleSubmit(e);
        }
    };

    const closeModal = () => { setActiveConnector(null); setConnectorForm({}); setConnectorMsg(null); };

    const activeDef = CONNECTOR_DEFS.find(d => d.id === activeConnector) ?? null;

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

                        {/* OAuth banner */}
                        {activeDef.oauth && (
                            <div className="flex items-start gap-2.5 bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 mb-4">
                                <svg className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                                </svg>
                                <p className="text-xs text-blue-700 leading-snug">
                                    {t('connector.oauthSecured', { service: activeDef.label })} {activeDef.id === 'sharepoint' ? t('connector.sharepointDetails') : ''} {t('connector.thenClick')} <strong>{t('connector.connect')}</strong>.
                                </p>
                            </div>
                        )}

                        {/* Fields */}
                        <div className="flex flex-col gap-3 mb-4">
                            {activeDef.fields.map(field => (
                                <div key={field.key}>
                                    <label className="block text-[11px] mb-1.5 font-semibold uppercase tracking-wider" style={{ color: tc.modalLabel }}>{field.label}</label>
                                    <input
                                        type="text"
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
                                {connectorSaving ? t('connector.connecting') : activeDef.oauth ? t('connector.connectService', { service: activeDef.label }) : t('connector.saveConnection')}
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
                                {/* Model selection */}
                                <div className="relative" ref={modelBadgeRef}>
                                    <button
                                        onClick={() => setIsModelPopupOpen(prev => !prev)}
                                        className={`rounded-md px-2 py-1 text-xs flex items-center gap-1.5 transition-colors cursor-pointer border ${isMobile ? 'font-medium' : 'font-normal'}`}
                                        style={tc.modelBtn}
                                        aria-label={t('query.selectModel')}
                                    >
                                        <svg className="w-3 h-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                        </svg>
                                        {selectedModel === 'auto' ? t('query.autoModel') : selectedModel}
                                        <svg className="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                                        </svg>
                                    </button>

                                    {/* Model selection popup */}
                                    {isModelPopupOpen && (
                    <div
                        ref={modelPopupRef}
                        className="absolute bottom-full left-0 mb-2 w-64 bg-white border border-gray-200 rounded-xl shadow-xl z-50 overflow-hidden"
                    >
                                            <div className="px-3 py-2 border-b border-gray-100">
                                                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t('model.selectModel')}</p>
                                            </div>
                                            <div className="max-h-64 overflow-y-auto">
                                                {[
                                                    { id: 'auto', name: t('model.auto'), provider: t('model.provider.smartSelector') },
                                                    { id: 'gpt-3.5-turbo', name: t('model.gpt-3.5-turbo'), provider: t('model.provider.OpenAI') },
                                                    { id: 'gpt-4o', name: t('model.gpt-4o'), provider: t('model.provider.OpenAI') },
                                                    { id: 'gpt-5', name: t('model.gpt-5'), provider: t('model.provider.OpenAI') },
                                                    { id: 'mistral', name: t('model.mistral'), provider: t('model.provider.MistralAI') },
                                                    { id: 'llama3', name: t('model.llama3'), provider: t('model.provider.Local') }
                                                ].map((model) => (
                                                    <button
                                                        key={model.id}
                                                        onClick={() => {
                                                            setSelectedModel(model.id);
                                                            setIsModelPopupOpen(false);
                                                        }}
                                                        className={`w-full text-left px-3 py-2 flex items-center gap-2.5 hover:bg-gray-50 transition-colors border-b border-gray-50 last:border-0 ${
                                                            selectedModel === model.id ? 'bg-blue-50' : ''
                                                        }`}
                                                    >
                                                        <div className="flex-1 min-w-0">
                                                            <div className={`text-xs font-medium break-words whitespace-normal ${
                                                                selectedModel === model.id ? 'text-blue-700' : 'text-gray-800'
                                                            }`}>
                                                                {model.name}
                                                                {model.id === 'gpt-5' && (
                                                                    <span className="ml-1.5 inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium bg-green-100 text-green-700">{t('model.latest')}</span>
                                                                )}
                                                            </div>
                                                            <div className="text-[10px] text-gray-400 break-words whitespace-normal">{model.provider}</div>
                                                        </div>
                                                        {selectedModel === model.id && (
                                                            <svg className="w-4 h-4 text-blue-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                                            </svg>
                                                        )}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>

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
                        disabled={loading || !query.trim()}
                        className={`
                            rounded-xl p-2
                            ${loading || !query.trim()
                                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                : 'bg-gradient-to-br from-blue-500 via-blue-600 to-indigo-600 hover:shadow-lg hover:shadow-blue-500/30 active:scale-90 text-white'
                            }
                            transition-all duration-200 border border-transparent
                        `}
                        aria-label={t('query.submit')}
                    >
                                {loading ? (
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
                    <div className="mt-3 flex items-center justify-center gap-3">
                        {CONNECTOR_DEFS.map(({ id, label, icon }) => (
                            <button
                                key={id}
                                title={t('connector.connectService', { service: label })}
                                onClick={() => { setActiveConnector(id); setConnectorForm({}); setConnectorMsg(null); }}
                                className="w-8 h-8 flex items-center justify-center rounded-full border hover:border-purple-400 hover:scale-110 hover:shadow-sm transition-all duration-200"
                                style={tc.connBtn}
                                aria-label={t('connector.connect', { service: label })}
                            >
                                <span className="w-4 h-4 flex items-center justify-center">{icon}</span>
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AppHomeComponent;