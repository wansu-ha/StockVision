import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-950 text-gray-100">
          <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-xl shadow p-8 text-center">
            <h1 className="text-xl font-bold mb-4">오류가 발생했습니다</h1>
            <p className="text-gray-400 text-sm mb-6">
              예기치 않은 오류가 발생했습니다. 새로고침을 시도해주세요.
            </p>
            {import.meta.env.DEV && this.state.error && (
              <pre className="text-left text-xs text-red-400 bg-red-900/20 border border-red-800/30 rounded-lg p-3 mb-6 overflow-auto max-h-40">
                {this.state.error.message}
              </pre>
            )}
            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="px-4 py-2 text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-xl hover:bg-gray-700 transition"
              >
                다시 시도
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-xl hover:bg-indigo-500 transition"
              >
                새로고침
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
