'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useRouter } from 'next/navigation';
import { Shield, AlertTriangle, FileCode, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { listRuns, Issue, Run } from '@/lib/api';

export default function IssuesPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [issues, setIssues] = useState<(Issue & { run_id: string; repo_url: string })[]>([]);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  useEffect(() => {
    const fetchAllIssues = async () => {
      try {
        // REAL API CALL: GET /api/v1/runs
        const response = await fetch(`${API_URL}/runs?page_size=20`);
        if (!response.ok) {
          throw new Error(`Failed to fetch runs: ${response.status}`);
        }
        const data = await response.json();

        // Collect all issues from all runs
        const allIssues: (Issue & { run_id: string; repo_url: string })[] = [];

        for (const run of data.runs || []) {
          // REAL API CALL: GET /api/v1/runs/{runId}
          const runResponse = await fetch(`${API_URL}/runs/${run.id}`);
          if (runResponse.ok) {
            const runData = await runResponse.json();
            runData.issues?.forEach((issue: Issue) => {
              allIssues.push({
                ...issue,
                run_id: run.id,
                repo_url: run.repo_url,
              });
            });
          }
        }

        setIssues(allIssues);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Failed to load issues');
      } finally {
        setIsLoading(false);
      }
    };

    fetchAllIssues();
  }, [API_URL]);

  const severityColors: Record<string, string> = {
    critical: 'bg-red-500',
    high: 'bg-orange-500',
    medium: 'bg-amber-500',
    low: 'bg-blue-500',
  };

  const getRepoName = (url: string) => {
    const parts = url.split('/');
    return parts.slice(-2).join('/');
  };

  return (
    <div className="min-h-screen bg-slate-950">
      <header className="border-b border-slate-800/50 backdrop-blur-sm sticky top-0 z-50 bg-slate-950/80">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => router.push('/')}>
            <Shield className="h-8 w-8 text-emerald-400" />
            <span className="text-xl font-bold tracking-tight">CodeSentinel</span>
          </div>
          <nav className="flex items-center gap-6">
            <a href="/dashboard" className="text-slate-400 hover:text-white">Dashboard</a>
            <a href="/runs" className="text-slate-400 hover:text-white">Runs</a>
            <a href="/issues" className="text-emerald-400 font-medium">Issues</a>
          </nav>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">All Issues</h1>
          <p className="text-slate-400 mt-1">Issues found across all repositories</p>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
          </div>
        ) : error ? (
          <Card className="bg-red-900/20 border-red-500/50">
            <CardContent className="py-8 text-center">
              <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
              <p className="text-red-400">{error}</p>
            </CardContent>
          </Card>
        ) : issues.length === 0 ? (
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="py-12 text-center">
              <AlertTriangle className="h-12 w-12 text-slate-500 mx-auto mb-4" />
              <p className="text-slate-400">No issues found yet</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {issues.map((issue) => (
              <motion.div
                key={issue.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <Card
                  className="bg-slate-900/50 border-slate-800 hover:border-emerald-500/50 transition-colors cursor-pointer"
                  onClick={() => router.push(`/runs/${issue.run_id}`)}
                >
                  <CardContent className="py-4">
                    <div className="flex items-start gap-4">
                      <AlertTriangle className="h-5 w-5 text-red-400 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <span className="font-medium">{issue.title}</span>
                          <Badge className={`${severityColors[issue.severity] || 'bg-slate-500'} text-white capitalize`}>
                            {issue.severity}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-slate-400">
                          {issue.file_path && (
                            <div className="flex items-center gap-1">
                              <FileCode className="h-4 w-4" />
                              {issue.file_path}{issue.line_number ? `:${issue.line_number}` : ''}
                            </div>
                          )}
                          <div>|</div>
                          <div>{getRepoName(issue.repo_url)}</div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
