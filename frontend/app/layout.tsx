import type { Metadata, Viewport } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Research Coach — AI 价值投资研究训练助手',
  description:
    '面向买方投研团队、投研实习生和初级研究员的价值投资研究训练工具。基于公司研究资料包完成证据抽取、价值投资框架分析、买方 Memo 生成。',
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#0a0f1a',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="zh-CN"
      style={{ backgroundColor: 'oklch(0.10 0.005 240)' }}
    >
      <body className="font-sans antialiased" style={{ backgroundColor: 'oklch(0.10 0.005 240)', color: 'oklch(0.93 0.005 240)' }}>
        {children}
      </body>
    </html>
  )
}
