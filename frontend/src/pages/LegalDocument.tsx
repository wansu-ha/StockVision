import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Markdown from 'react-markdown'
import cloudClient from '../services/cloudClient'

const TITLES: Record<string, string> = {
  terms: '이용약관',
  privacy: '개인정보처리방침',
  disclaimer: '투자 위험 고지',
}

interface LegalDocData {
  doc_type: string
  version: string
  title: string
  content_md: string
  effective_date: string | null
}

export default function LegalDocument() {
  const { type } = useParams<{ type: string }>()
  const docType = type ?? ''

  const { data, isLoading, error } = useQuery<LegalDocData>({
    queryKey: ['legalDoc', docType],
    queryFn: async () => {
      const resp = await cloudClient.get(`/api/v1/legal/documents/${docType}`)
      return resp.data.data
    },
    staleTime: 30 * 60_000,
    enabled: !!docType && docType in TITLES,
  })

  if (!docType || !(docType in TITLES)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center text-gray-400">
          <p className="text-lg mb-4">문서를 찾을 수 없습니다</p>
          <Link to="/" className="text-indigo-400 hover:text-indigo-300 transition">홈으로</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-3xl mx-auto px-6 py-8">
        <Link to="/" className="text-sm text-gray-500 hover:text-gray-300 transition mb-6 inline-block">
          &larr; StockVision
        </Link>

        <h1 className="text-2xl font-bold mb-2">{TITLES[docType]}</h1>
        {data?.version && (
          <div className="text-sm text-gray-500 mb-6">
            버전 {data.version}
            {data.effective_date && <> &middot; 시행일 {data.effective_date}</>}
          </div>
        )}

        {isLoading ? (
          <div className="py-16 text-center text-gray-500">불러오는 중...</div>
        ) : error ? (
          <div className="py-16 text-center text-red-400">문서를 불러올 수 없습니다</div>
        ) : !data?.content_md ? (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-gray-400 text-sm leading-relaxed">
            약관 내용이 아직 등록되지 않았습니다.
          </div>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <div className="prose prose-invert prose-sm max-w-none text-gray-300 leading-relaxed">
              <Markdown>{data.content_md}</Markdown>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
