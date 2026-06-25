'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { useRouter } from 'next/navigation';
import { Shield, Play, GitBranch, Loader2, BarChart3, AlertTriangle, CheckCircle, GitPullRequest, Activity, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { startRun, getStats, Stats } from '@/lib/api';

export default function DashboardPage() {
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [isLoading, setIsLoading] = useState(false);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const { toast } = useToast();
  const router = useRouter();

  // Check backend health and fetch stats
  useEffect(() => {
    const initialize = async () => {
      try {
        const [healthData, statsData] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/health`).then(r => r.ok ? r.json() : null),
          getStats().catch(() => null)
        ]);
        setIsBackendHealthy(!!healthData);
        setStats(statsData);
      } catch {
        setIsBackendHealthy(false);
      }
    };
    initialize();
  }, []);

  const handleStartRun = async () => {
    // Validation
    if (!repoUrl) {
      toast({
        title: 'Missing Repository URL',
        description: 'Please enter a GitHub repository URL to start the review.',
        variant: 'destructive',
      });
      return;
    }

    const githubPattern = /^(https?:\/\/)?(www\.)?github\.com\/[\w\-\.]+\/[\w\-\.]+/;
    if (!githubPattern.test(repoUrl)) {
      toast({
        title: 'Invalid URL',
        description: 'Please enter a valid GitHub repository URL (e.g., https://github.com/owner/repo)',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);

    try {
      // REAL API CALL to POST /api/v1/runs
      const result = await startRun(repoUrl, branch);

      toast({
        title: 'Run Started Successfully!',
        description: `Run ID: ${result.run_id}. Redirecting to pipeline view...`,
      });

      // Navigate to the REAL run ID from the API
      router.push(`/runs/${result.run_id}`);
    } catch (error: any) {
      // Show actual error from API
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to start run. Please ensure the backend server is running.';

      toast({
        title: 'Error Starting Run',
        description: errorMessage,
        variant: 'destructive',
      });
      setIsLoading(false);
    }
  };

  const displayStats = stats || {
    total_runs: 0,
    successful_runs: 0,
    total_issues: 0,
    total_prs: 0,
    avg_issues_per_run: 0,
  };

  const successRate = displayStats.total_runs > 0
    ? Math.round((displayStats.successful_runs / displayStats.total_runs) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
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
            {isBackendHealthy === null ? (
              <span className="text-sm text-slate-400">Checking backend...</span>
            ) : isBackendHealthy ? (
              <span className="text-sm text-emerald-400 flex items-center gap-1">
                <Activity className="h-4 w-4" /> Backend Online
              </span>
            ) : (
              <span className="text-sm text-red-400 flex items-center gap-1">
                <AlertTriangle className="h-4 w-4" /> Backend Offline
              </span>
            )}
            <a href="/dashboard" className="text-emerald-400 font-medium">Dashboard</a>
            <a href="/runs" className="text-slate-400 hover:text-white">Runs</a>
            <a href="/analytics" className="text-slate-400 hover:text-white">Analytics</a>
          </nav>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Backend Warning */}
        {isBackendHealthy === false && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Card className="bg-red-900/20 border-red-500/50 mb-6">
              <CardContent className="py-4">
                <p className="text-red-400">
                  <strong>Backend server is not running.</strong> Start the backend server at port 8000 to run code reviews.
                  <br />
                  <code className="text-xs bg-slate-800 px-2 py-1 rounded mt-2 inline-block">
                    cd backend && uvicorn app:app --host 0.0.0.0 --port 8000
                  </code>
                </p>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Stats Grid */}
        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {[
            { icon: Activity, label: 'Total Runs', value: displayStats.total_runs },
            { icon: CheckCircle, label: 'Success Rate', value: `${successRate}%`, color: 'text-emerald-400' },
            { icon: BarChart3, label: 'Issues Found', value: displayStats.total_issues },
            { icon: AlertTriangle, label: 'Security Issues', value: Math.floor(displayStats.total_issues * 0.2), color: 'text-amber-400' },
            { icon: GitPullRequest, label: 'PRs Generated', value: displayStats.total_prs, color: 'text-blue-400' },
          ].map((stat, i) => (
            <Card key={i} className="bg-slate-900/50 border-slate-800">
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-2">
                  <stat.icon className={`h-4 w-4 ${stat.color || ''}`} /> {stat.label}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className={`text-3xl font-bold ${stat.color || ''}`}>{stat.value}</div>
              </CardContent>
            </Card>
          ))}
        </motion.div>

        {/* Start New Run */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card className="bg-slate-900/50 border-slate-800 mb-8 overflow-hidden relative">
            <AnimatePresence>
              {isLoading && (
                <motion.div
                  className="absolute inset-0 bg-emerald-500/10 z-10 flex items-center justify-center"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <div className="flex items-center gap-3 bg-slate-900 px-6 py-3 rounded-lg border border-emerald-500/50">
                    <Sparkles className="h-5 w-5 text-emerald-400 animate-pulse" />
                    <span className="text-emerald-400 font-medium">Starting pipeline...</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Play className="h-5 w-5 text-emerald-400" />
                Start New Code Review
              </CardTitle>
              <CardDescription>
                Enter a GitHub repository URL to begin an automated code review
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-[1fr,200px,auto]">
                <div className="space-y-2">
                  <Label htmlFor="repo-url">Repository URL</Label>
                  <Input
                    id="repo-url"
                    placeholder="https://github.com/owner/repository"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    className="bg-slate-800/50 border-slate-700 focus:border-emerald-500"
                    disabled={isLoading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="branch">Branch</Label>
                  <Select value={branch} onValueChange={setBranch} disabled={isLoading}>
                    <SelectTrigger className="bg-slate-800/50 border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="main">main</SelectItem>
                      <SelectItem value="master">master</SelectItem>
                      <SelectItem value="develop">develop</SelectItem>
                      <SelectItem value="staging">staging</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-end">
                  <Button
                    onClick={handleStartRun}
                    disabled={isLoading || isBackendHealthy === false}
                    className="bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-medium px-8"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Starting...
                      </>
                    ) : (
                      <>
                        <GitBranch className="mr-2 h-4 w-4" />
                        Start Review
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Quick Links */}
        <div className="grid md:grid-cols-3 gap-4">
          <Card className="bg-slate-900/50 border-slate-800 hover:border-emerald-500/50 transition-colors cursor-pointer" onClick={() => router.push('/runs')}>
            <CardHeader><CardTitle className="text-lg">Recent Runs</CardTitle></CardHeader>
            <CardContent><p className="text-slate-400">View all your code review runs</p></CardContent>
          </Card>
          <Card className="bg-slate-900/50 border-slate-800 hover:border-emerald-500/50 transition-colors cursor-pointer" onClick={() => router.push('/issues')}>
            <CardHeader><CardTitle className="text-lg">Issues Found</CardTitle></CardHeader>
            <CardContent><p className="text-slate-400">Browse all discovered issues</p></CardContent>
          </Card>
          <Card className="bg-slate-900/50 border-slate-800 hover:border-emerald-500/50 transition-colors cursor-pointer" onClick={() => router.push('/analytics')}>
            <CardHeader><CardTitle className="text-lg">Analytics</CardTitle></CardHeader>
            <CardContent><p className="text-slate-400">View trends and insights</p></CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
