import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const features = [
  {
    icon: '🎓',
    title: 'College-Specific Answers',
    desc:  'Ask anything about your college — syllabus, notices, timetables, exam schedules.',
  },
  {
    icon: '⚡',
    title: 'Instant AI Responses',
    desc:  'Powered by Groq + LLaMA 3. Answers in under a second, grounded in real documents.',
  },
  {
    icon: '🔒',
    title: 'Secure & Isolated',
    desc:  'Each college has its own private data space. No cross-college data leakage ever.',
  },
  {
    icon: '📄',
    title: 'Document Management',
    desc:  'Admins upload PDFs, syllabi, notices. Students get accurate answers instantly.',
  },
  {
    icon: '📊',
    title: 'Usage Analytics',
    desc:  'Track most-asked questions, active users, and engagement across your college.',
  },
  {
    icon: '🏫',
    title: 'Multi-College SaaS',
    desc:  'One platform, many colleges. Each institution gets their own isolated workspace.',
  },
]

export default function Landing() {
  const { user } = useAuth()

  return (
    <div className="min-h-screen bg-gray-950 text-white">

      {/* Navbar */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🎓</span>
          <span className="text-xl font-bold text-white">ChatDEVA</span>
        </div>
        <div className="flex items-center gap-4">
          {user ? (
            <>
              <Link to="/chat"
                className="text-gray-300 hover:text-white transition">
                My Chat
              </Link>
              {['admin', 'staff'].includes(user.role) && (
                <Link to="/admin"
                  className="text-gray-300 hover:text-white transition">
                  Admin Panel
                </Link>
              )}
            </>
          ) : (
            <Link to="/login"
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg font-medium transition">
              Get Started
            </Link>
          )}
        </div>
      </nav>

      {/* Hero */}
      <section className="text-center py-24 px-6 max-w-4xl mx-auto">
        <div className="inline-block bg-indigo-900/40 text-indigo-300 text-sm px-4 py-1 rounded-full mb-6 border border-indigo-700">
          AI-Powered College Assistant
        </div>
        <h1 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
          Ask anything about
          <span className="text-indigo-400"> your college</span>
        </h1>
        <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
          ChatDEVA gives students instant, accurate answers from their college's
          own documents — syllabus, notices, timetables, exam schedules, and more.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link to="/login"
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-3 rounded-xl font-semibold text-lg transition">
            Start Chatting →
          </Link>
<a href="#features"
            className="border border-gray-600 hover:border-gray-400 text-gray-300 hover:text-white px-8 py-3 rounded-xl font-semibold text-lg transition">
            See Features
          </a>
        </div>
      </section>

      {/* Demo preview */}
      <section className="max-w-3xl mx-auto px-6 mb-20">
        <div className="bg-gray-900 rounded-2xl border border-gray-700 p-6 shadow-2xl">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <span className="ml-2 text-gray-500 text-sm">ChatDEVA</span>
          </div>
          <div className="space-y-4">
            <div className="flex justify-end">
              <div className="bg-indigo-600 text-white px-4 py-2 rounded-2xl rounded-tr-sm max-w-xs text-sm">
                What topics are in the Data Structures syllabus?
              </div>
            </div>
            <div className="flex gap-3">
              <div className="w-8 h-8 bg-indigo-700 rounded-full flex items-center justify-center text-sm flex-shrink-0">
                🎓
              </div>
              <div className="bg-gray-800 text-gray-200 px-4 py-2 rounded-2xl rounded-tl-sm max-w-sm text-sm">
                Based on your college's syllabus, Data Structures covers:
                Arrays, Linked Lists, Stacks, Queues, Trees, Graphs, Sorting algorithms, and Hashing.
                <div className="mt-2 text-indigo-400 text-xs">
                  📘 CS-301-Syllabus.pdf · syllabus
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-6 pb-24">
        <h2 className="text-3xl font-bold text-center mb-12">
          Everything your college needs
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f) => (
            <div key={f.title}
              className="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-indigo-700 transition">
              <div className="text-3xl mb-3">{f.icon}</div>
              <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="text-center py-20 px-6 border-t border-gray-800">
        <h2 className="text-3xl font-bold mb-4">Ready to get started?</h2>
        <p className="text-gray-400 mb-8">
          Join your college's ChatDEVA workspace today.
        </p>
        <Link to="/login"
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-10 py-3 rounded-xl font-semibold text-lg transition">
          Get Started Free →
        </Link>
      </section>

      {/* Footer */}
      <footer className="text-center py-6 text-gray-600 text-sm border-t border-gray-800">
        © 2026 ChatDEVA · AI-powered college assistant
      </footer>
    </div>
  )
}
