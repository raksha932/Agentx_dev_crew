-- Runs table
CREATE TABLE runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    repo_url TEXT NOT NULL,
    branch TEXT NOT NULL DEFAULT 'main',
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_message TEXT
);

-- Issues table
CREATE TABLE issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium',
    description TEXT,
    file_path TEXT,
    line_number INTEGER,
    code_snippet TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Root causes table
CREATE TABLE root_causes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    cause TEXT NOT NULL,
    impact TEXT,
    confidence REAL DEFAULT 0.0,
    reasoning TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fixes table
CREATE TABLE fixes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    patch TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    explanation TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pull requests table
CREATE TABLE pull_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    github_pr_number INTEGER,
    pr_url TEXT,
    status TEXT DEFAULT 'pending',
    title TEXT,
    body TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent executions table
CREATE TABLE agent_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    agent_order INTEGER NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'pending',
    logs JSONB DEFAULT '[]',
    result JSONB,
    progress INTEGER DEFAULT 0
);

-- Enable RLS
ALTER TABLE runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE root_causes ENABLE ROW LEVEL SECURITY;
ALTER TABLE fixes ENABLE ROW LEVEL SECURITY;
ALTER TABLE pull_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_executions ENABLE ROW LEVEL SECURITY;

-- RLS Policies for runs
CREATE POLICY "select_own_runs" ON runs FOR SELECT
    TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "insert_own_runs" ON runs FOR INSERT
    TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own_runs" ON runs FOR UPDATE
    TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "delete_own_runs" ON runs FOR DELETE
    TO authenticated USING (auth.uid() = user_id);

-- RLS Policies for issues
CREATE POLICY "select_own_issues" ON issues FOR SELECT
    TO authenticated USING (EXISTS (
        SELECT 1 FROM runs WHERE runs.id = issues.run_id AND runs.user_id = auth.uid()
    ));
CREATE POLICY "insert_own_issues" ON issues FOR INSERT
    TO authenticated WITH CHECK (EXISTS (
        SELECT 1 FROM runs WHERE runs.id = issues.run_id AND runs.user_id = auth.uid()
    ));

-- RLS Policies for root_causes
CREATE POLICY "select_own_root_causes" ON root_causes FOR SELECT
    TO authenticated USING (EXISTS (
        SELECT 1 FROM issues JOIN runs ON runs.id = issues.run_id
        WHERE issues.id = root_causes.issue_id AND runs.user_id = auth.uid()
    ));
CREATE POLICY "insert_own_root_causes" ON root_causes FOR INSERT
    TO authenticated WITH CHECK (EXISTS (
        SELECT 1 FROM issues JOIN runs ON runs.id = issues.run_id
        WHERE issues.id = root_causes.issue_id AND runs.user_id = auth.uid()
    ));

-- RLS Policies for fixes
CREATE POLICY "select_own_fixes" ON fixes FOR SELECT
    TO authenticated USING (EXISTS (
        SELECT 1 FROM issues JOIN runs ON runs.id = issues.run_id
        WHERE issues.id = fixes.issue_id AND runs.user_id = auth.uid()
    ));
CREATE POLICY "insert_own_fixes" ON fixes FOR INSERT
    TO authenticated WITH CHECK (EXISTS (
        SELECT 1 FROM issues JOIN runs ON runs.id = issues.run_id
        WHERE issues.id = fixes.issue_id AND runs.user_id = auth.uid()
    ));

-- RLS Policies for pull_requests
CREATE POLICY "select_own_pull_requests" ON pull_requests FOR SELECT
    TO authenticated USING (EXISTS (
        SELECT 1 FROM runs WHERE runs.id = pull_requests.run_id AND runs.user_id = auth.uid()
    ));
CREATE POLICY "insert_own_pull_requests" ON pull_requests FOR INSERT
    TO authenticated WITH CHECK (EXISTS (
        SELECT 1 FROM runs WHERE runs.id = pull_requests.run_id AND runs.user_id = auth.uid()
    ));

-- RLS Policies for agent_executions
CREATE POLICY "select_own_agent_executions" ON agent_executions FOR SELECT
    TO authenticated USING (EXISTS (
        SELECT 1 FROM runs WHERE runs.id = agent_executions.run_id AND runs.user_id = auth.uid()
    ));
CREATE POLICY "insert_own_agent_executions" ON agent_executions FOR INSERT
    TO authenticated WITH CHECK (EXISTS (
        SELECT 1 FROM runs WHERE runs.id = agent_executions.run_id AND runs.user_id = auth.uid()
    ));

-- Indexes
CREATE INDEX idx_runs_user_id ON runs(user_id);
CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_issues_run_id ON issues(run_id);
CREATE INDEX idx_root_causes_issue_id ON root_causes(issue_id);
CREATE INDEX idx_fixes_issue_id ON fixes(issue_id);
CREATE INDEX idx_pull_requests_run_id ON pull_requests(run_id);
CREATE INDEX idx_agent_executions_run_id ON agent_executions(run_id);