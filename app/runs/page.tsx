'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';
import { Shield, Play, Loader2, GitBranch, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Run {
  id: string;
  repo_url: string;
  branch: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  issues_count?: number;
}

const statusConfig = {
  queued: { color: 'bg-slate-500', icon: Clock },
  running: { color: 'bg-blue-500', icon: Loader2 },
  completed: { color: 'bg-emerald-500', icon: CheckCircle },
  failed: { color: 'bg-red-500', icon: XCircle },
  cancelled: { color: 'bg-amber-500', icon: XCircle },
};

export default function RunsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [runs, setRuns] = useState<Run[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  useEffect(() => {
    const fetchRuns = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // REAL API CALL: GET /api/v1/runs
        const response = await fetch(`${API_URL}/runs`);
        if (!response.ok) {
          throw new Error(`Failed to fetch runs: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        setRuns(data.runs || []);
        setTotal(data.total || 0);
      } catch (err: any) {
        setError(err.message || 'Failed to load runs. Ensure backend is running.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchRuns();
  }, [API_URL]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getRepoName = (url: string) => {
    const parts = url.split('/');
    return parts.slice(-2).join('/');
  };

  return (
    <div className="min-h-screen bg-slate-950">
      <header className="border-b border-slate-800/50 backdrop-blur-sm sticky top-0 z-50 bg-slate-950/80">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <motion.div
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => router.push('/')}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <Shield className="h-8 w-8 text-emerald-400" />
            <span className="text-xl font-bold tracking-tight">CodeSentinel</span>
          </motion.div>
          <nav className="flex items-center gap-6">
            <a href="/dashboard" className="text-slate-400 hover:text-white">Dashboard</a>
            <a href="/runs" className="text-emerald-400 font-medium">Runs</a>
            <a href="/analytics" className="text-slate-400 hover:text-white">Analytics</a>
          </nav>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <motion.div
          className="flex items-center justify-between mb-8"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div>
            <h1 className="text-3xl font-bold">Code Review Runs</h1>
            <p className="text-slate-400 mt-1">View and manage your code review history</p>
          </div>
          <Button onClick={() => router.push('/dashboard')} className="bg-emerald-500 hover:bg-emerald-600 text-slate-950">
            <Play className="mr-2 h-4 w-4" /> New Run
          </Button>
        </motion.div>

        {error && (
          <Card className="bg-red-900/20 border-red-500/50 mb-6">
            <CardContent className="py-4 flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 text-red-400" />
              <p className="text-red-400">{error}</p>
            </CardContent>
          </Card>
        )}

        <AnimatePresence mode="wait">
          {isLoading ? (
            <motion.div key="loading" className="flex items-center justify-center py-20" exit={{ opacity: 0 }}>
              <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
            </motion.div>
          ) : runs.length === 0 ? (
            <motion.div key="empty" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <Card className="bg-slate-900/50 border-slate-800">
                <CardContent className="py-12 text-center">
                  <Clock className="h-12 w-12 text-slate-500 mx-auto mb-4" />
                  <p className="text-slate-400 mb-4">No runs found</p>
                  <Button onClick={() => router.push('/dashboard')} className="bg-emerald-500 hover:bg-emerald-600 text-slate-950">
                    Start Your First Review
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          ) : (
            <motion.div key="content" className="space-y-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              {runs.map((run, index) => {
                const config = statusConfig[run.status as keyof typeof statusConfig] || statusConfig.queued;
                const StatusIcon = config.icon;

                return (
                  <motion.div
                    key={run.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <Card
                      className="bg-slate-900/50 border-slate-800 hover:border-emerald-500/50 transition-all cursor-pointer"
                      onClick={() => router.push(`/runs/${run.id}`)}
                    >
                      <CardContent className="py-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className={`w-3 h-3 rounded-full ${config.color}`} />
                            <div>
                              <div className="font-medium flex items-center gap-2">
                                <GitBranch className="h-4 w-4 text-slate-400" />
                                {getRepoName(run.repo_url)}
                              </div>
                              <div className="text-sm text-slate-400 mt-1">
                                {run.branch} • {formatDate(run.created_at)}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-4">
                            {run.issues_count !== undefined && run.issues_count > 0 && (
                              <Badge variant="secondary" className="bg-slate-800">
                                {run.issues_count} issues
                              </Badge>
                            )}
                            <Badge className={`${config.color} text-white capitalize flex items-center gap-1.5`}>
                              <StatusIcon className={`h-3 w-3 ${run.status === 'running' ? 'animate-spin' : ''}`} />
                              {run.status}
                            </Badge>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                );
              })}

              {total > runs.length && (
                <p className="text-center text-slate-400 py-4">
                  Showing {runs.length} of {total} runs
                </p>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
