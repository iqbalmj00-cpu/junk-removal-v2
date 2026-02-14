'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { ShieldCheck, AlertTriangle, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface LiabilityWaiverProps {
    companyName?: string;
    onAccept: (signatureDataUrl: string) => void;
    onBack: () => void;
}

export default function LiabilityWaiver({
    companyName = 'Clean Sweep Junk Removal',
    onAccept,
    onBack,
}: LiabilityWaiverProps) {
    const [isOwnerChecked, setIsOwnerChecked] = useState(false);
    const [isTermsChecked, setIsTermsChecked] = useState(false);
    const [hasSigned, setHasSigned] = useState(false);
    const [signatureError, setSignatureError] = useState(false);

    const canvasRef = useRef<HTMLCanvasElement>(null);
    const isDrawingRef = useRef(false);
    const lastPosRef = useRef({ x: 0, y: 0 });

    const isFormValid = isOwnerChecked && isTermsChecked && hasSigned;

    // --- Canvas setup ---
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const resizeCanvas = () => {
            const rect = canvas.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;
            const ctx = canvas.getContext('2d');
            if (ctx) {
                ctx.scale(dpr, dpr);
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';
                ctx.lineWidth = 2.5;
                ctx.strokeStyle = '#1e293b';
            }
        };

        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
        return () => window.removeEventListener('resize', resizeCanvas);
    }, []);

    // --- Drawing helpers ---
    const getPos = useCallback((e: React.MouseEvent | React.TouchEvent) => {
        const canvas = canvasRef.current;
        if (!canvas) return { x: 0, y: 0 };
        const rect = canvas.getBoundingClientRect();
        if ('touches' in e) {
            return {
                x: e.touches[0].clientX - rect.left,
                y: e.touches[0].clientY - rect.top,
            };
        }
        return { x: e.clientX - rect.left, y: e.clientY - rect.top };
    }, []);

    const startDraw = useCallback((e: React.MouseEvent | React.TouchEvent) => {
        e.preventDefault();
        isDrawingRef.current = true;
        lastPosRef.current = getPos(e);
        setSignatureError(false);
    }, [getPos]);

    const draw = useCallback((e: React.MouseEvent | React.TouchEvent) => {
        if (!isDrawingRef.current) return;
        e.preventDefault();
        const canvas = canvasRef.current;
        const ctx = canvas?.getContext('2d');
        if (!ctx) return;

        const pos = getPos(e);
        ctx.beginPath();
        ctx.moveTo(lastPosRef.current.x, lastPosRef.current.y);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
        lastPosRef.current = pos;
        setHasSigned(true);
    }, [getPos]);

    const endDraw = useCallback(() => {
        isDrawingRef.current = false;
    }, []);

    const clearSignature = () => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        const dpr = window.devicePixelRatio || 1;
        ctx.clearRect(0, 0, canvas.width / dpr, canvas.height / dpr);
        setHasSigned(false);
    };

    const handleSubmit = () => {
        if (!hasSigned) {
            setSignatureError(true);
            canvasRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }
        if (!isFormValid) return;

        const canvas = canvasRef.current;
        if (!canvas) return;
        const dataUrl = canvas.toDataURL('image/png');
        onAccept(dataUrl);
    };

    // --- Legal text sections ---
    const legalSections = [
        {
            title: 'Damage Waiver',
            text: `I acknowledge that junk removal involves heavy lifting and moving items through my property. I release ${companyName} from liability for minor scuffs, scratches, or damage to floors/walls that may occur during the normal course of work.`,
        },
        {
            title: 'Hazardous Materials',
            text: `I certify that my junk does not contain hazardous materials (chemicals, asbestos, medical waste). I understand I will be liable for any disposal fees or fines if such items are found concealed in my load.`,
        },
        {
            title: 'Payment Terms',
            text: `I understand the price given is an estimate based on volume. Final price is confirmed onsite. If I decline the onsite price, there is no obligation.`,
        },
        {
            title: 'Image Release',
            text: `I grant permission for ${companyName} to take before/after photos of the work area for proof of service and marketing purposes.`,
        },
    ];

    return (
        <div className="max-w-2xl mx-auto animate-in fade-in slide-in-from-right-8 duration-500">
            <Button
                variant="ghost"
                onClick={onBack}
                className="text-slate-400 hover:text-slate-900 font-bold px-0 mb-6"
            >
                ← Back to Booking Details
            </Button>

            <div className="bg-white rounded-[2rem] shadow-xl border border-slate-100 p-8 md:p-12">
                {/* Header */}
                <div className="flex items-center gap-4 mb-8">
                    <div className="w-14 h-14 bg-orange-100 text-brand-orange rounded-2xl flex items-center justify-center shrink-0">
                        <ShieldCheck size={28} strokeWidth={2.5} />
                    </div>
                    <div>
                        <h2 className="text-2xl md:text-3xl font-bold text-slate-900">
                            Terms & Liability Release
                        </h2>
                        <p className="text-slate-500 text-sm md:text-base">
                            Please review and sign below to authorize our crew to work on your property.
                        </p>
                    </div>
                </div>

                {/* Scrollable Legal Text */}
                <div className="mb-8">
                    <div className="h-[220px] overflow-y-auto border border-slate-200 rounded-xl bg-slate-50 p-5 space-y-5 scrollbar-thin">
                        {legalSections.map((section, i) => (
                            <div key={i}>
                                <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wide mb-1">
                                    {i + 1}. {section.title}
                                </h4>
                                <p className="text-sm text-slate-600 leading-relaxed">
                                    {section.text}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Checkboxes */}
                <div className="space-y-4 mb-8">
                    <label className="flex items-start gap-3 cursor-pointer group">
                        <input
                            type="checkbox"
                            checked={isOwnerChecked}
                            onChange={() => setIsOwnerChecked(!isOwnerChecked)}
                            className="mt-1 h-5 w-5 rounded border-slate-300 text-brand-orange focus:ring-brand-orange/30 cursor-pointer"
                        />
                        <span className="text-sm text-slate-700 group-hover:text-slate-900 transition-colors leading-relaxed">
                            I certify that I am the <strong>property owner</strong> or an <strong>authorized agent</strong> with permission to request junk removal services at this address.
                        </span>
                    </label>

                    <label className="flex items-start gap-3 cursor-pointer group">
                        <input
                            type="checkbox"
                            checked={isTermsChecked}
                            onChange={() => setIsTermsChecked(!isTermsChecked)}
                            className="mt-1 h-5 w-5 rounded border-slate-300 text-brand-orange focus:ring-brand-orange/30 cursor-pointer"
                        />
                        <span className="text-sm text-slate-700 group-hover:text-slate-900 transition-colors leading-relaxed">
                            I have read and agree to the <strong>Terms of Service</strong> and <strong>Liability Release</strong> above.
                        </span>
                    </label>
                </div>

                {/* Signature Pad */}
                <div className="mb-8">
                    <div className="flex items-center justify-between mb-2">
                        <label className="text-sm font-bold text-slate-700">
                            Sign with your finger or mouse
                        </label>
                        {hasSigned && (
                            <span className="text-xs font-semibold text-green-600 bg-green-50 px-2 py-1 rounded-full">
                                ✓ Saved
                            </span>
                        )}
                    </div>
                    <div
                        className={`relative rounded-xl border-2 transition-colors ${signatureError
                                ? 'border-red-400 ring-2 ring-red-100'
                                : hasSigned
                                    ? 'border-green-300'
                                    : 'border-slate-200 hover:border-slate-300'
                            }`}
                    >
                        <canvas
                            ref={canvasRef}
                            className="w-full h-[140px] cursor-crosshair rounded-xl bg-white touch-none"
                            onMouseDown={startDraw}
                            onMouseMove={draw}
                            onMouseUp={endDraw}
                            onMouseLeave={endDraw}
                            onTouchStart={startDraw}
                            onTouchMove={draw}
                            onTouchEnd={endDraw}
                        />
                        {!hasSigned && (
                            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                                <span className="text-slate-300 text-lg font-light italic">
                                    Draw your signature here
                                </span>
                            </div>
                        )}
                    </div>
                    {signatureError && (
                        <p className="text-red-500 text-xs mt-2 flex items-center gap-1">
                            <AlertTriangle size={14} />
                            Please sign above to continue
                        </p>
                    )}
                    <button
                        type="button"
                        onClick={clearSignature}
                        className="mt-2 text-xs text-slate-400 hover:text-red-500 transition-colors flex items-center gap-1"
                    >
                        <Trash2 size={12} /> Clear Signature
                    </button>
                </div>

                {/* Submit */}
                <Button
                    onClick={handleSubmit}
                    disabled={!isFormValid}
                    className={`w-full h-16 text-xl font-bold rounded-full shadow-xl transition-all duration-300 ${isFormValid
                            ? 'bg-brand-orange hover:bg-orange-600 text-white shadow-orange-900/20 cursor-pointer'
                            : 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                        }`}
                >
                    Agree & Continue
                </Button>

                {!isFormValid && (
                    <p className="text-center text-xs text-slate-400 mt-3">
                        {!isOwnerChecked || !isTermsChecked
                            ? 'Check both boxes above to continue'
                            : 'Sign above to continue'}
                    </p>
                )}
            </div>
        </div>
    );
}
