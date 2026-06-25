'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';
import { Shield, GitBranch, Zap, Bot, Code, Lock, ArrowRight, Github, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';

const features = [
  {
    icon: Bot,
    title: '9-Agent AI Pipeline',
    description: 'LangGraph-orchestrated agents work together to analyze, fix, and validate your code.',
  },
  {
    icon: Shield,
    title: 'Security Scanning',
    description: 'OWASP vulnerability detection, secrets scanning, and dependency analysis built-in.',
  },
  {
    icon: Code,
    title: 'Root Cause Analysis',
    description: 'AI identifies underlying issues and generates targeted fixes with confidence scores.',
  },
  {
    icon: GitBranch,
    title: 'Automated PRs',
    description: 'Generated fixes are packaged into review-ready pull requests automatically.',
  },
  {
    icon: Zap,
    title: 'Real-Time Updates',
    description: 'Watch your code review progress live with WebSocket-powered streaming.',
  },
  {
    icon: Lock,
    title: 'Safe & Validated',
    description: 'Every fix is validated and tested before being suggested for merge.',
  },
];

const agents = [
  { name: 'Orchestrator', order: 1, desc: 'Validates requests, manages state' },
  { name: 'Repository Intelligence', order: 2, desc: 'Clones repos, builds context' },
  { name: 'Code Analysis', order: 3, desc: 'AST analysis, bug detection' },
  { name: 'Security Scanner', order: 4, desc: 'OWASP, secrets, dependencies' },
  { name: 'Root Cause Analysis', order: 5, desc: 'Causal chains, impact assessment' },
  { name: 'Fix Generator', order: 6, desc: 'Generates patches, preserves contracts' },
  { name: 'Validation Agent', order: 7, desc: 'Reviews fixes, confidence scoring' },
  { name: 'Verification Agent', order: 8, desc: 'Runs tests, checks regressions' },
  { name: 'PR Creation', order: 9, desc: 'Creates GitHub PRs, uploads artifacts' },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 backdrop-blur-sm sticky top-0 z-50 bg-slate-950/80">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <motion.div
            className="flex items-center gap-3"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <Shield className="h-8 w-8 text-emerald-400" />
            <span className="text-xl font-bold tracking-tight">CodeSentinel</span>
          </motion.div>
          <motion.nav
            className="flex items-center gap-6"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <Link href="/dashboard" className="text-slate-400 hover:text-white transition-colors">
              Dashboard
            </Link>
            <Link href="/runs" className="text-slate-400 hover:text-white transition-colors">
              Runs
            </Link>
            <Link href="/dashboard">
              <Button className="bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-medium transition-all duration-300">
                Get Started
              </Button>
            </Link>
          </motion.nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-8">
            <Zap className="h-4 w-4 text-emerald-400" />
            <span className="text-emerald-400 text-sm font-medium">Powered by AI</span>
          </div>
        </motion.div>

        <motion.h1
          className="text-5xl md:text-7xl font-bold tracking-tight mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <span className="text-white">Autonomous </span>
          <span className="text-emerald-400">Code Review</span>
        </motion.h1>

        <motion.p
          className="text-xl text-slate-400 max-w-2xl mx-auto mb-12"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          AI-powered platform that automatically analyzes your code, identifies issues,
          generates fixes, and creates pull requests. All in real-time.
        </motion.p>

        <motion.div
          className="flex items-center justify-center gap-4 flex-wrap"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Link href="/dashboard">
            <Button size="lg" className="bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold px-8 h-12 transition-all duration-300 hover:scale-105">
              Start Reviewing <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </Link>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer">
            <Button size="lg" variant="outline" className="border-slate-700 hover:bg-slate-800 px-8 h-12 transition-all duration-300 hover:scale-105">
              <Github className="mr-2 h-5 w-5" /> View on GitHub
            </Button>
          </a>
        </motion.div>
      </section>

      {/* Features Grid */}
      <section className="container mx-auto px-4 py-20">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Built for Modern Development</h2>
          <p className="text-slate-400 max-w-xl mx-auto">
            A comprehensive suite of AI agents working together to deliver production-ready code fixes.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
            >
              <Card className="bg-slate-900/50 border-slate-800 hover:border-emerald-500/50 transition-all duration-300 hover:scale-[1.02] h-full">
                <CardHeader>
                  <feature.icon className="h-10 w-10 text-emerald-400 mb-2" />
                  <CardTitle className="text-lg">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-slate-400">{feature.description}</CardDescription>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Agent Pipeline */}
      <section className="container mx-auto px-4 py-20">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4">9-Agent Pipeline</h2>
          <p className="text-slate-400 max-w-xl mx-auto">
            Each agent specializes in a specific task, working together to deliver complete code reviews.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-4">
          {agents.map((agent, i) => (
            <motion.div
              key={agent.order}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className="flex items-start gap-4 p-4 rounded-lg bg-slate-900/30 border border-slate-800 hover:border-emerald-500/30 transition-all duration-300"
            >
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
                <span className="text-emerald-400 text-sm font-bold">{agent.order}</span>
              </div>
              <div>
                <h3 className="font-medium text-white mb-1">{agent.name}</h3>
                <p className="text-sm text-slate-400">{agent.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <Card className="bg-gradient-to-r from-emerald-900/20 to-slate-900/50 border-emerald-500/20 overflow-hidden relative">
            <CardContent className="py-16 text-center">
              <h2 className="text-3xl font-bold mb-4">Ready to improve your code?</h2>
              <p className="text-slate-400 mb-8 max-w-lg mx-auto">
                Enter a GitHub repository URL and let CodeSentinel analyze your code in minutes.
              </p>
              <Link href="/dashboard">
                <Button size="lg" className="bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold px-8 h-12 transition-all duration-300 hover:scale-105">
                  Start Your First Review <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 py-8">
        <div className="container mx-auto px-4 text-center text-slate-500 text-sm">
          <p>Built with Next.js, FastAPI, LangGraph, and Google Gemini</p>
        </div>
      </footer>
    </div>
  );
}
