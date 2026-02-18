import { Cpu, MessageSquare, Brain, Heart, Zap } from 'lucide-react';

const FEATURES = [
  {
    icon: Heart,
    title: 'Emotional Intelligence',
    desc: 'ระบบ EVC จำลองฮอร์โมน 8 ตัวเพื่อสร้างอารมณ์ที่สมจริง',
    color: 'text-pink-400',
  },
  {
    icon: Brain,
    title: 'Memory & Context',
    desc: 'จดจำรายละเอียดและบริบทของคุณข้าม session',
    color: 'text-emerald-400',
  },
  {
    icon: Zap,
    title: 'Smart Skills',
    desc: 'ทักษะเฉพาะทาง: เตือนนัด, ดูแลอารมณ์, จำข้อมูล',
    color: 'text-amber-400',
  },
];

export default function WelcomeScreen() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
      <div className="w-16 h-16 rounded-2xl bg-jarvis-700/20 border border-jarvis-600/30 flex items-center justify-center mb-6">
        <Cpu size={32} className="text-jarvis-400" />
      </div>

      <h2 className="text-xl font-bold text-white mb-2">สวัสดีครับ ผม Jarvis</h2>
      <p className="text-sm text-[#888] max-w-md mb-8">
        AI เลขาส่วนตัวที่มีอารมณ์และความทรงจำ พร้อมดูแลและช่วยเหลือคุณ
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl w-full">
        {FEATURES.map((f) => (
          <div
            key={f.title}
            className="bg-[#1a1c24] border border-[#2a2d37] rounded-xl p-4 text-left hover:border-jarvis-700/50 transition-colors"
          >
            <f.icon size={20} className={`${f.color} mb-2`} />
            <h3 className="text-xs font-semibold text-white mb-1">{f.title}</h3>
            <p className="text-[11px] text-[#777] leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>

      <div className="mt-8 flex items-center gap-2 text-[11px] text-[#555]">
        <MessageSquare size={12} />
        <span>พิมพ์ข้อความด้านล่างเพื่อเริ่มสนทนา</span>
      </div>
    </div>
  );
}
