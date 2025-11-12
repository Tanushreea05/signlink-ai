import Link from 'next/link'
import { Camera, Sparkles, Globe, Shield } from 'lucide-react'

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-16">
        <nav className="flex justify-between items-center mb-16">
          <div className="text-2xl font-bold text-blue-600">SignLink AI</div>
          <div className="space-x-4">
            <Link href="/login" className="text-gray-600 hover:text-gray-900">
              Login
            </Link>
            <Link 
              href="/register" 
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
            >
              Get Started
            </Link>
          </div>
        </nav>

        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
            Break Communication Barriers with{' '}
            <span className="text-blue-600">AI-Powered Sign Language</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Real-time sign language recognition and translation. Connect with anyone, anywhere.
          </p>
          <div className="flex gap-4 justify-center">
            <Link 
              href="/translate" 
              className="bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 flex items-center gap-2"
            >
              <Camera className="w-5 h-5" />
              Start Translating
            </Link>
            <Link 
              href="/demo" 
              className="border-2 border-blue-600 text-blue-600 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-50"
            >
              Watch Demo
            </Link>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 mt-24">
          <div className="bg-white p-8 rounded-xl shadow-lg">
            <div className="bg-blue-100 w-12 h-12 rounded-lg flex items-center justify-center mb-4">
              <Sparkles className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Real-time Recognition</h3>
            <p className="text-gray-600">
              Instant sign language detection with 94%+ accuracy using advanced AI models.
            </p>
          </div>

          <div className="bg-white p-8 rounded-xl shadow-lg">
            <div className="bg-blue-100 w-12 h-12 rounded-lg flex items-center justify-center mb-4">
              <Globe className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Multi-Language Support</h3>
            <p className="text-gray-600">
              Supports ASL, ISL, BSL and more sign languages with continuous updates.
            </p>
          </div>

          <div className="bg-white p-8 rounded-xl shadow-lg">
            <div className="bg-blue-100 w-12 h-12 rounded-lg flex items-center justify-center mb-4">
              <Shield className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Privacy First</h3>
            <p className="text-gray-600">
              End-to-end encryption and GDPR compliant. Your data stays private.
            </p>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-24 bg-blue-600 rounded-2xl p-12 text-white">
          <div className="grid md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-4xl font-bold mb-2">94.2%</div>
              <div className="text-blue-100">Model Accuracy</div>
            </div>
            <div>
              <div className="text-4xl font-bold mb-2">&lt;100ms</div>
              <div className="text-blue-100">Inference Time</div>
            </div>
            <div>
              <div className="text-4xl font-bold mb-2">3</div>
              <div className="text-blue-100">Sign Languages</div>
            </div>
            <div>
              <div className="text-4xl font-bold mb-2">24/7</div>
              <div className="text-blue-100">Availability</div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12 mt-24">
        <div className="container mx-auto px-4 text-center">
          <p className="text-gray-400">
            © 2025 SignLink AI. All rights reserved. | MIT License
          </p>
        </div>
      </footer>
    </main>
  )
}
