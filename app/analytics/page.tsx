'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Shield, BarChart3, TrendingUp, AlertTriangle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import { useRouter } from 'next/navigation';

const runsOverTime = [
  { name: 'Mon', runs: 4, issues: 12 },
  { name: 'Tue', runs: 3, issues: 8 },
  { name: 'Wed', runs: 6, issues: 15 },
  { name: 'Thu', runs: 5, issues: 11 },
  { name: 'Fri', runs: 8, issues: 22 },
  { name: 'Sat', runs: 2, issues: 4 },
  { name: 'Sun', runs: 1, issues: 3 },
];

const severityData = [
  { name: 'Critical', value: 12, color: '#ef4444' },
  { name: 'High', value: 28, color: '#f97316' },
  { name: 'Medium', value: 45, color: '#f59e0b' },
  { name: 'Low', value: 71, color: '#3b82f6' },
];

const agentPerformance = [
  { name: 'Orchestrator', time: 2 },
  { name: 'Repo Intel', time: 45 },
  { name: 'Code Analysis', time: 120 },
  { name: 'Security', time: 60 },
  { name: 'RCA', time: 90 },
  { name: 'Fix Gen', time: 150 },
  { name: 'Validation', time: 30 },
  { name: 'Verification', time: 80 },
  { name: 'PR Creation', time: 15 },
];

export default function AnalyticsPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 backdrop-blur-sm sticky top-0 z-50 bg-slate-950/80">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => router.push('/')}>
            <Shield className="h-8 w-8 text-emerald-400" />
            <span className="text-xl font-bold tracking-tight">CodeSentinel</span>
          </div>
          <nav className="flex items-center gap-6">
            <a href="/dashboard" className="text-slate-400 hover:text-white transition-colors">Dashboard</a>
            <a href="/runs" className="text-slate-400 hover:text-white transition-colors">Runs</a>
            <a href="/analytics" className="text-emerald-400 font-medium">Analytics</a>
          </nav>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Analytics</h1>
          <p className="text-slate-400 mt-1">Insights and trends from your code reviews</p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Runs Over Time */}
          <Card className="bg-slate-900/50 border-slate-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-emerald-400" />
                Runs Over Time
              </CardTitle>
              <CardDescription>Daily runs and issues found</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={runsOverTime}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none' }} />
                  <Line type="monotone" dataKey="runs" stroke="#10b981" strokeWidth={2} />
                  <Line type="monotone" dataKey="issues" stroke="#f59e0b" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Severity Distribution */}
          <Card className="bg-slate-900/50 border-slate-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-emerald-400" />
                Severity Distribution
              </CardTitle>
              <CardDescription>Issues by severity level</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={severityData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}
                  >
                    {severityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none' }} />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Agent Performance */}
          <Card className="bg-slate-900/50 border-slate-800 md:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-emerald-400" />
                Agent Performance
              </CardTitle>
              <CardDescription>Average execution time per agent (seconds)</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={agentPerformance} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis type="number" stroke="#94a3b8" />
                  <YAxis type="category" dataKey="name" stroke="#94a3b8" width={100} />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none' }} />
                  <Bar dataKey="time" fill="#10b981" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
