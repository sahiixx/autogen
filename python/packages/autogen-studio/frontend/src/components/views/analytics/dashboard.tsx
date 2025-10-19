import React, { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, Progress, Table, Tabs } from "antd";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  RocketOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  ApiOutlined,
  TeamOutlined,
} from "@ant-design/icons";

interface AnalyticsMetrics {
  total_sessions: number;
  total_messages: number;
  total_runs: number;
  avg_response_time: number;
  success_rate: number;
  active_teams: number;
  messages_per_session: number;
  popular_models: Array<{ model: string; usage: number }>;
  timeline_data: Array<{ date: string; runs: number; success_rate: number }>;
}

interface ModelComparison {
  model: string;
  runs: number;
  avg_response_time: number;
  success_rate: number;
  avg_tokens: number;
  cost_estimate: number;
}

const COLORS = ["#464feb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

export const AnalyticsDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<AnalyticsMetrics | null>(null);
  const [modelComparison, setModelComparison] = useState<ModelComparison[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState("7");

  useEffect(() => {
    fetchAnalytics();
  }, [selectedPeriod]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      
      // Fetch main metrics
      const metricsRes = await fetch(`/api/analytics/metrics?days=${selectedPeriod}`);
      const metricsData = await metricsRes.json();
      setMetrics(metricsData);

      // Fetch model comparison
      const modelsRes = await fetch(`/api/analytics/models/comparison?days=${selectedPeriod}`);
      const modelsData = await modelsRes.json();
      setModelComparison(modelsData.models);
      
    } catch (error) {
      console.error("Failed to fetch analytics:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !metrics) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
      </div>
    );
  }

  const modelColumns = [
    {
      title: "Model",
      dataIndex: "model",
      key: "model",
      render: (text: string) => <span className="font-medium">{text}</span>,
    },
    {
      title: "Runs",
      dataIndex: "runs",
      key: "runs",
      sorter: (a: ModelComparison, b: ModelComparison) => a.runs - b.runs,
    },
    {
      title: "Avg Response Time",
      dataIndex: "avg_response_time",
      key: "avg_response_time",
      render: (time: number) => `${time.toFixed(2)}s`,
    },
    {
      title: "Success Rate",
      dataIndex: "success_rate",
      key: "success_rate",
      render: (rate: number) => (
        <Progress
          percent={rate}
          size="small"
          strokeColor={rate > 95 ? "#10b981" : rate > 85 ? "#f59e0b" : "#ef4444"}
        />
      ),
    },
    {
      title: "Avg Tokens",
      dataIndex: "avg_tokens",
      key: "avg_tokens",
    },
    {
      title: "Cost Estimate",
      dataIndex: "cost_estimate",
      key: "cost_estimate",
      render: (cost: number) => `$${cost.toFixed(2)}`,
    },
  ];

  return (
    <div className="p-6 space-y-6 bg-primary">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-primary">Analytics Dashboard</h1>
          <p className="text-secondary">Monitor your agent performance and usage</p>
        </div>
        <select
          value={selectedPeriod}
          onChange={(e) => setSelectedPeriod(e.target.value)}
          className="px-4 py-2 border border-secondary rounded-lg bg-primary text-primary"
        >
          <option value="1">Last 24 hours</option>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="90">Last 90 days</option>
        </select>
      </div>

      {/* Key Metrics */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card className="bg-secondary border-secondary">
            <Statistic
              title="Total Runs"
              value={metrics.total_runs}
              prefix={<RocketOutlined className="text-accent" />}
              valueStyle={{ color: "var(--color-text-primary)" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="bg-secondary border-secondary">
            <Statistic
              title="Avg Response Time"
              value={metrics.avg_response_time}
              suffix="s"
              prefix={<ClockCircleOutlined className="text-blue-500" />}
              precision={2}
              valueStyle={{ color: "var(--color-text-primary)" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="bg-secondary border-secondary">
            <Statistic
              title="Success Rate"
              value={metrics.success_rate}
              suffix="%"
              prefix={<CheckCircleOutlined className="text-green-500" />}
              precision={1}
              valueStyle={{ color: "var(--color-text-primary)" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="bg-secondary border-secondary">
            <Statistic
              title="Active Teams"
              value={metrics.active_teams}
              prefix={<TeamOutlined className="text-purple-500" />}
              valueStyle={{ color: "var(--color-text-primary)" }}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="Usage Over Time" className="bg-secondary border-secondary">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={metrics.timeline_data}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-secondary)" />
                <XAxis dataKey="date" stroke="var(--color-text-secondary)" />
                <YAxis stroke="var(--color-text-secondary)" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--color-bg-tertiary)",
                    border: "1px solid var(--color-border-secondary)",
                    borderRadius: "8px",
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="runs"
                  stroke="#464feb"
                  strokeWidth={2}
                  name="Runs"
                />
                <Line
                  type="monotone"
                  dataKey="success_rate"
                  stroke="#10b981"
                  strokeWidth={2}
                  name="Success Rate %"
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="Model Usage" className="bg-secondary border-secondary">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={metrics.popular_models}
                  dataKey="usage"
                  nameKey="model"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label
                >
                  {metrics.popular_models.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--color-bg-tertiary)",
                    border: "1px solid var(--color-border-secondary)",
                    borderRadius: "8px",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* Model Comparison Table */}
      <Card title="Model Performance Comparison" className="bg-secondary border-secondary">
        <Table
          dataSource={modelComparison}
          columns={modelColumns}
          rowKey="model"
          pagination={false}
          className="model-comparison-table"
        />
      </Card>

      {/* Additional Insights */}
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card title="Quick Insights" className="bg-secondary border-secondary">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <ThunderboltOutlined className="text-yellow-500 text-xl" />
                <div>
                  <div className="font-medium text-primary">Peak Usage Hour</div>
                  <div className="text-sm text-secondary">2:00 PM - 3:00 PM</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <ApiOutlined className="text-blue-500 text-xl" />
                <div>
                  <div className="font-medium text-primary">Most Used Feature</div>
                  <div className="text-sm text-secondary">Multi-Agent Workflows</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <CheckCircleOutlined className="text-green-500 text-xl" />
                <div>
                  <div className="font-medium text-primary">Best Performing Team</div>
                  <div className="text-sm text-secondary">Research Assistant (98.5% success)</div>
                </div>
              </div>
            </div>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card title="Cost Summary" className="bg-secondary border-secondary">
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-secondary">Estimated Total Cost</span>
                  <span className="font-bold text-lg text-accent">
                    ${modelComparison.reduce((sum, m) => sum + m.cost_estimate, 0).toFixed(2)}
                  </span>
                </div>
                <Progress
                  percent={65}
                  strokeColor="#464feb"
                  trailColor="var(--color-bg-tertiary)"
                />
                <div className="text-xs text-secondary mt-1">65% of monthly budget</div>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-secondary">
                <div>
                  <div className="text-sm text-secondary">Avg Cost/Run</div>
                  <div className="text-lg font-bold text-primary">$0.18</div>
                </div>
                <div>
                  <div className="text-sm text-secondary">Total Tokens</div>
                  <div className="text-lg font-bold text-primary">125K</div>
                </div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AnalyticsDashboard;
