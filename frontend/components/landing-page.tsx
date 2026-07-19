'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'

interface LandingPageProps {
  onEnterApp: () => void
  onLogin: () => void
  onSignup: () => void
}

const features = [
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M3 14L7 9L10 11.5L14 6L17 8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
        <circle cx="17" cy="8" r="1.5" fill="currentColor"/>
        <path d="M3 17h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.4"/>
      </svg>
    ),
    title: '持续研究工作台',
    desc: '围绕研究问题、证据、Thesis和答辩持续更新，同一公司无需每次从头开始。',
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <rect x="3" y="3" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.6"/>
        <rect x="11" y="3" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.6"/>
        <rect x="3" y="11" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.6"/>
        <rect x="11" y="11" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.6"/>
      </svg>
    ),
    title: '证据标注与来源追溯',
    desc: '每条结论都标注【事实 / 观点 / 假设 / AI推理】四种类型，并附来源说明，杜绝卖方观点直接复读。',
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M10 3L12.5 8H17L13 11.5L14.5 17L10 14L5.5 17L7 11.5L3 8H7.5L10 3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
      </svg>
    ),
    title: '结构化买方 Memo',
    desc: '自动生成 11 节标准买方研究 Memo，覆盖现金流、分红、商业模式、价值陷阱等价值投资核心维度。',
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M4 5h12M4 10h8M4 15h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
        <circle cx="15" cy="14" r="3" stroke="currentColor" strokeWidth="1.5"/>
        <path d="M17 16l1.5 1.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
    title: '报告批改模式',
    desc: '粘贴初级研究员报告，AI 按价值投资准则批改，识别高股息误判、卖方复读、反证意识缺失等典型问题。',
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M10 2v16M2 10h16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity="0.3"/>
        <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.6"/>
        <path d="M10 6v4l3 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    title: '价值投资框架驱动',
    desc: '以 7 个价值投资核心维度为分析骨架，专注可验证的财务事实，不做荐股，不生成无来源结论。',
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M3 6h14v10a1 1 0 01-1 1H4a1 1 0 01-1-1V6z" stroke="currentColor" strokeWidth="1.6"/>
        <path d="M3 6l2-3h10l2 3" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
        <path d="M8 10l2 2 4-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    title: '合规门禁机制',
    desc: '内置 Pre/Post Memo 双重合规检查，自动屏蔽收益承诺表达，确保输出符合研究规范。',
  },
]

const workflowSteps = [
  { num: '01', name: 'Research Map', desc: '建立问题树与研究优先级' },
  { num: '02', name: 'Evidence', desc: '维护资料库、证据关系与冲突' },
  { num: '03', name: 'Thesis', desc: '形成变量、反证与三种情景' },
  { num: '04', name: 'Memo', desc: '共同完成可追溯研究报告' },
  { num: '05', name: 'Defense & Feedback', desc: '答辩、任务回流与能力成长' },
]

const stats = [
  { value: '7', label: '价值投资分析维度' },
  { value: '5', label: '核心研究任务区' },
  { value: '4', label: '证据标注类型' },
  { value: '11', label: 'Memo 标准章节' },
]

export function LandingPage({ onEnterApp, onLogin, onSignup }: LandingPageProps) {
  return (
    <div className="min-h-screen" style={{ backgroundColor: 'oklch(0.10 0.005 240)', color: 'oklch(0.93 0.005 240)' }}>

      {/* ── Navigation ── */}
      <header
        className="sticky top-0 z-50 border-b"
        style={{
          borderColor: 'oklch(0.22 0.01 240)',
          backgroundColor: 'oklch(0.10 0.005 240 / 0.95)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <div className="mx-auto max-w-screen-xl px-6">
          <div className="flex h-14 items-center justify-between">
            {/* Logo */}
            <div className="flex items-center gap-2.5">
              <div
                className="flex h-7 w-7 items-center justify-center rounded"
                style={{ backgroundColor: 'oklch(0.65 0.14 195)' }}
              >
                <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
                  <path d="M3 12L6 7L9 9.5L12 4" stroke="oklch(0.10 0.005 240)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <circle cx="12" cy="4" r="1.5" fill="oklch(0.10 0.005 240)"/>
                </svg>
              </div>
              <span className="text-sm font-semibold" style={{ color: 'oklch(0.93 0.005 240)' }}>Research Coach</span>
            </div>

            {/* Center nav */}
            <nav className="hidden md:flex items-center gap-6">
              {[
                { label: '功能特性', id: 'section-features' },
                { label: '工作流程', id: 'section-workflow' },
                { label: '适用场景', id: 'section-usecases' },
              ].map(item => (
                <button
                  key={item.label}
                  className="text-sm transition-colors"
                  style={{ color: 'oklch(0.55 0.01 240)' }}
                  onMouseEnter={e => (e.currentTarget.style.color = 'oklch(0.93 0.005 240)')}
                  onMouseLeave={e => (e.currentTarget.style.color = 'oklch(0.55 0.01 240)')}
                  onClick={() => document.getElementById(item.id)?.scrollIntoView({ behavior: 'smooth' })}
                >
                  {item.label}
                </button>
              ))}
            </nav>

            {/* Auth buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={onLogin}
                className="px-4 py-1.5 text-sm rounded-md transition-colors"
                style={{ color: 'oklch(0.75 0.01 240)' }}
                onMouseEnter={e => (e.currentTarget.style.color = 'oklch(0.93 0.005 240)')}
                onMouseLeave={e => (e.currentTarget.style.color = 'oklch(0.75 0.01 240)')}
              >
                登录
              </button>
              <button
                onClick={onEnterApp}
                className="px-4 py-1.5 text-sm font-medium rounded-md transition-opacity hover:opacity-90"
                style={{
                  backgroundColor: 'oklch(0.65 0.14 195)',
                  color: 'oklch(0.10 0.005 240)',
                }}
              >
                免费试用
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="mx-auto max-w-screen-xl px-6 pt-24 pb-20">
        <div className="text-center max-w-3xl mx-auto">
          {/* Tag line */}
          <div className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs mb-8"
            style={{
              borderColor: 'oklch(0.65 0.14 195 / 0.35)',
              backgroundColor: 'oklch(0.65 0.14 195 / 0.08)',
              color: 'oklch(0.65 0.14 195)',
            }}
          >
            <span className="h-1.5 w-1.5 rounded-full animate-pulse" style={{ backgroundColor: 'oklch(0.65 0.14 195)' }} />
            专为买方投研训练设计
          </div>

          {/* Headline */}
          <h1
            className="text-5xl font-bold leading-tight tracking-tight mb-6 text-balance"
            style={{ color: 'oklch(0.93 0.005 240)' }}
          >
            用 AI 建立
            <span style={{ color: 'oklch(0.65 0.14 195)' }}> 价值投资</span>
            <br />研究思维框架
          </h1>

          <p
            className="text-lg leading-relaxed mb-10 text-pretty max-w-xl mx-auto"
            style={{ color: 'oklch(0.60 0.01 240)' }}
          >
            为投研实习生和初级研究员提供结构化研究训练。上传研究资料，AI 按照机构买方准则完成分析，每条结论都有来源可溯，不是荐股工具。
          </p>

          {/* CTA */}
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={onSignup}
              className="flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-semibold transition-opacity hover:opacity-90"
              style={{
                backgroundColor: 'oklch(0.65 0.14 195)',
                color: 'oklch(0.10 0.005 240)',
              }}
            >
              免费注册，开始分析
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3 7h8M8 4l3 3-3 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
            <button
              onClick={onLogin}
              className="px-6 py-3 rounded-lg text-sm font-medium border transition-colors"
              style={{
                borderColor: 'oklch(0.28 0.01 240)',
                color: 'oklch(0.75 0.01 240)',
                backgroundColor: 'transparent',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'oklch(0.45 0.01 240)'
                e.currentTarget.style.color = 'oklch(0.93 0.005 240)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'oklch(0.28 0.01 240)'
                e.currentTarget.style.color = 'oklch(0.75 0.01 240)'
              }}
            >
              已有账户，登录
            </button>
          </div>
        </div>

        {/* Stats bar */}
        <div
          className="grid grid-cols-4 gap-px mt-20 rounded-xl overflow-hidden border"
          style={{ borderColor: 'oklch(0.22 0.01 240)', backgroundColor: 'oklch(0.22 0.01 240)' }}
        >
          {stats.map(stat => (
            <div
              key={stat.label}
              className="px-6 py-5 text-center"
              style={{ backgroundColor: 'oklch(0.13 0.008 240)' }}
            >
              <div
                className="text-3xl font-bold tabular-nums"
                style={{ color: 'oklch(0.65 0.14 195)' }}
              >
                {stat.value}
              </div>
              <div className="text-xs mt-1" style={{ color: 'oklch(0.55 0.01 240)' }}>
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ── */}
      <section
        id="section-features"
        className="border-t"
        style={{ borderColor: 'oklch(0.18 0.01 240)' }}
      >
        <div className="mx-auto max-w-screen-xl px-6 py-20">
          <div className="mb-12">
            <div
              className="text-xs font-mono uppercase tracking-widest mb-3"
              style={{ color: 'oklch(0.65 0.14 195)' }}
            >
              功能特性
            </div>
            <h2
              className="text-3xl font-bold text-balance"
              style={{ color: 'oklch(0.93 0.005 240)' }}
            >
              训练思维，而不是给出答案
            </h2>
            <p className="mt-3 text-sm max-w-xl" style={{ color: 'oklch(0.55 0.01 240)' }}>
              区别于荐股工具，Research Coach 关注研究过程本身：证据从哪来、结论是否可追溯、有哪些反证风险。
            </p>
          </div>

          <div className="grid grid-cols-3 gap-4">
            {features.map((f, i) => (
              <div
                key={i}
                className="rounded-xl border p-5 transition-all"
                style={{
                  borderColor: 'oklch(0.22 0.01 240)',
                  backgroundColor: 'oklch(0.13 0.008 240)',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'oklch(0.65 0.14 195 / 0.4)'
                  e.currentTarget.style.backgroundColor = 'oklch(0.15 0.01 240)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'oklch(0.22 0.01 240)'
                  e.currentTarget.style.backgroundColor = 'oklch(0.13 0.008 240)'
                }}
              >
                <div
                  className="h-9 w-9 rounded-lg flex items-center justify-center mb-4"
                  style={{
                    backgroundColor: 'oklch(0.65 0.14 195 / 0.12)',
                    color: 'oklch(0.65 0.14 195)',
                  }}
                >
                  {f.icon}
                </div>
                <h3
                  className="text-sm font-semibold mb-2"
                  style={{ color: 'oklch(0.90 0.005 240)' }}
                >
                  {f.title}
                </h3>
                <p className="text-xs leading-relaxed" style={{ color: 'oklch(0.55 0.01 240)' }}>
                  {f.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Workflow ── */}
      <section
        id="section-workflow"
        className="border-t"
        style={{ borderColor: 'oklch(0.18 0.01 240)', backgroundColor: 'oklch(0.12 0.007 240)' }}
      >
        <div className="mx-auto max-w-screen-xl px-6 py-20">
          <div className="grid grid-cols-2 gap-16 items-center">
            {/* Left text */}
            <div>
              <div
                className="text-xs font-mono uppercase tracking-widest mb-3"
                style={{ color: 'oklch(0.75 0.15 75)' }}
              >
                工作流程
              </div>
              <h2
                className="text-3xl font-bold mb-4 text-balance"
                style={{ color: 'oklch(0.93 0.005 240)' }}
              >
                证据驱动研究
                <br />闭环
              </h2>
              <p className="text-sm leading-relaxed mb-6" style={{ color: 'oklch(0.55 0.01 240)' }}>
                从研究任务、资料库和证据图谱出发，逐步形成Thesis、Memo与投委会答辩，并把每次训练沉淀为个人能力画像。
              </p>
              <button
                onClick={onSignup}
                className="flex items-center gap-2 text-sm font-medium transition-opacity hover:opacity-80"
                style={{ color: 'oklch(0.65 0.14 195)' }}
              >
                注册后体验完整流程
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M3 7h8M8 4l3 3-3 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            </div>

            {/* Right: workflow steps */}
            <div className="space-y-2">
              {workflowSteps.map((step, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-lg px-4 py-3 border"
                  style={{
                    borderColor: 'oklch(0.22 0.01 240)',
                    backgroundColor: 'oklch(0.14 0.008 240)',
                  }}
                >
                  <span
                    className="text-xs font-mono shrink-0 w-7"
                    style={{ color: 'oklch(0.65 0.14 195)' }}
                  >
                    {step.num}
                  </span>
                  <div className="flex-1 min-w-0">
                    <span className="text-xs font-medium" style={{ color: 'oklch(0.88 0.005 240)' }}>
                      {step.name}
                    </span>
                    <span className="text-xs ml-2" style={{ color: 'oklch(0.50 0.01 240)' }}>
                      {step.desc}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Use Cases ── */}
      <section
        id="section-usecases"
        className="border-t"
        style={{ borderColor: 'oklch(0.18 0.01 240)' }}
      >
        <div className="mx-auto max-w-screen-xl px-6 py-20">
          <div className="mb-12">
            <div
              className="text-xs font-mono uppercase tracking-widest mb-3"
              style={{ color: 'oklch(0.65 0.14 195)' }}
            >
              适用场景
            </div>
            <h2 className="text-3xl font-bold text-balance" style={{ color: 'oklch(0.93 0.005 240)' }}>
              为投研学习者设计
            </h2>
          </div>

          <div className="grid grid-cols-3 gap-4">
            {[
              {
                title: '投研实习生',
                desc: '上传研究资料，跟随 AI 完成完整研究流程，理解买方研究逻辑，学会区分事实、观点与推理。',
                tag: '研究分析',
                tagColor: 'oklch(0.65 0.14 195)',
                tagBg: 'oklch(0.65 0.14 195 / 0.1)',
              },
              {
                title: '初级研究员',
                desc: '将自己写的研究报告提交 AI 审阅，识别卖方复读、价值陷阱误判、反证意识缺失等典型问题。',
                tag: '报告审阅',
                tagColor: 'oklch(0.75 0.15 75)',
                tagBg: 'oklch(0.75 0.15 75 / 0.1)',
              },
              {
                title: '买方团队',
                desc: '统一研究框架与输出标准，让每位研究员的 Memo 都符合机构准则，降低内部培训成本。',
                tag: '团队协作',
                tagColor: 'oklch(0.68 0.15 148)',
                tagBg: 'oklch(0.68 0.15 148 / 0.1)',
              },
            ].map((card, i) => (
              <div
                key={i}
                className="rounded-xl border p-6"
                style={{
                  borderColor: 'oklch(0.22 0.01 240)',
                  backgroundColor: 'oklch(0.13 0.008 240)',
                }}
              >
                <div
                  className="inline-flex items-center rounded-md px-2.5 py-1 text-xs font-medium mb-4"
                  style={{ color: card.tagColor, backgroundColor: card.tagBg }}
                >
                  {card.tag}
                </div>
                <h3 className="text-base font-semibold mb-2" style={{ color: 'oklch(0.90 0.005 240)' }}>
                  {card.title}
                </h3>
                <p className="text-sm leading-relaxed" style={{ color: 'oklch(0.55 0.01 240)' }}>
                  {card.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Bottom ── */}
      <section
        className="border-t"
        style={{
          borderColor: 'oklch(0.18 0.01 240)',
          backgroundColor: 'oklch(0.12 0.007 240)',
        }}
      >
        <div className="mx-auto max-w-screen-xl px-6 py-20 text-center">
          <h2
            className="text-3xl font-bold mb-4 text-balance"
            style={{ color: 'oklch(0.93 0.005 240)' }}
          >
            开始你的第一个研究分析
          </h2>
          <p className="text-sm mb-8" style={{ color: 'oklch(0.55 0.01 240)' }}>
            无需准备完整资料包，粘贴公司财务摘要即可开始。
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={onSignup}
              className="flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-semibold transition-opacity hover:opacity-90"
              style={{
                backgroundColor: 'oklch(0.65 0.14 195)',
                color: 'oklch(0.10 0.005 240)',
              }}
            >
              免费注册，开始分析
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3 7h8M8 4l3 3-3 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
            <button
              onClick={onLogin}
              className="px-6 py-3 rounded-lg text-sm font-medium border transition-colors"
              style={{
                borderColor: 'oklch(0.28 0.01 240)',
                color: 'oklch(0.75 0.01 240)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'oklch(0.45 0.01 240)'
                e.currentTarget.style.color = 'oklch(0.93 0.005 240)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'oklch(0.28 0.01 240)'
                e.currentTarget.style.color = 'oklch(0.75 0.01 240)'
              }}
            >
              已有账户，登录
            </button>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer
        className="border-t px-6 py-8"
        style={{ borderColor: 'oklch(0.18 0.01 240)' }}
      >
        <div className="mx-auto max-w-screen-xl flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div
              className="flex h-5 w-5 items-center justify-center rounded"
              style={{ backgroundColor: 'oklch(0.65 0.14 195)' }}
            >
              <svg width="11" height="11" viewBox="0 0 16 16" fill="none">
                <path d="M3 12L6 7L9 9.5L12 4" stroke="oklch(0.10 0.005 240)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="12" cy="4" r="1.5" fill="oklch(0.10 0.005 240)"/>
              </svg>
            </div>
            <span className="text-xs font-medium" style={{ color: 'oklch(0.55 0.01 240)' }}>
              Research Coach · 价值投资研究训练助手
            </span>
          </div>
          <p className="text-xs" style={{ color: 'oklch(0.40 0.01 240)' }}>
            本工具仅作为研究训练用途，不构成任何形式的投资建议
          </p>
        </div>
      </footer>
    </div>
  )
}
