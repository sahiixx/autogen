import React, { useEffect, useState } from "react";
import { Card, Row, Col, Tag, Button, Modal, Input, Select } from "antd";
import {
  RocketOutlined,
  TeamOutlined,
  CodeOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  CustomerServiceOutlined,
  SearchOutlined,
} from "@ant-design/icons";

interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  agents_count: number;
  complexity: string;
  use_cases: string[];
}

const categoryIcons: Record<string, React.ReactNode> = {
  support: <CustomerServiceOutlined />,
  research: <SearchOutlined />,
  development: <CodeOutlined />,
  content: <FileTextOutlined />,
  data: <DatabaseOutlined />,
};

const complexityColors: Record<string, string> = {
  low: "green",
  medium: "orange",
  high: "red",
};

export const TemplateLibrary: React.FC = () => {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [filteredTemplates, setFilteredTemplates] = useState<WorkflowTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  useEffect(() => {
    fetchTemplates();
  }, []);

  useEffect(() => {
    filterTemplates();
  }, [searchTerm, selectedCategory, templates]);

  const fetchTemplates = async () => {
    try {
      const response = await fetch("/api/export/templates");
      const data = await response.json();
      setTemplates(data);
      setFilteredTemplates(data);
    } catch (error) {
      console.error("Failed to fetch templates:", error);
    } finally {
      setLoading(false);
    }
  };

  const filterTemplates = () => {
    let filtered = templates;

    if (searchTerm) {
      filtered = filtered.filter(
        (t) =>
          t.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          t.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
          t.use_cases.some((uc) => uc.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    if (selectedCategory !== "all") {
      filtered = filtered.filter((t) => t.category === selectedCategory);
    }

    setFilteredTemplates(filtered);
  };

  const handleUseTemplate = async (template: WorkflowTemplate) => {
    try {
      // Fetch full template configuration
      const response = await fetch(`/api/export/templates/${template.id}`);
      const config = await response.json();
      
      // Navigate to build page with template config
      window.location.href = `/build?template=${template.id}`;
    } catch (error) {
      console.error("Failed to load template:", error);
    }
  };

  const categories = [
    { value: "all", label: "All Categories" },
    { value: "support", label: "Support" },
    { value: "research", label: "Research" },
    { value: "development", label: "Development" },
    { value: "content", label: "Content" },
    { value: "data", label: "Data" },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-primary">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-primary">Workflow Templates</h1>
          <p className="text-secondary">Get started quickly with pre-built templates</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <Input
          placeholder="Search templates..."
          prefix={<SearchOutlined />}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="max-w-md"
          size="large"
        />
        <Select
          value={selectedCategory}
          onChange={setSelectedCategory}
          options={categories}
          className="w-48"
          size="large"
        />
      </div>

      {/* Templates Grid */}
      <Row gutter={[16, 16]}>
        {filteredTemplates.map((template) => (
          <Col xs={24} sm={12} lg={8} key={template.id}>
            <Card
              className="bg-secondary border-secondary hover:border-accent transition-all h-full"
              hoverable
              onClick={() => setSelectedTemplate(template)}
            >
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="text-3xl text-accent">
                      {categoryIcons[template.category] || <RocketOutlined />}
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-primary">{template.name}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <Tag color={complexityColors[template.complexity]}>
                          {template.complexity.toUpperCase()}
                        </Tag>
                        <span className="text-sm text-secondary">
                          <TeamOutlined /> {template.agents_count} agents
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Description */}
                <p className="text-secondary text-sm line-clamp-2">{template.description}</p>

                {/* Use Cases */}
                <div className="flex flex-wrap gap-2">
                  {template.use_cases.slice(0, 3).map((useCase, idx) => (
                    <Tag key={idx} className="text-xs">
                      {useCase}
                    </Tag>
                  ))}
                </div>

                {/* Actions */}
                <Button
                  type="primary"
                  block
                  onClick={(e) => {
                    e.stopPropagation();
                    handleUseTemplate(template);
                  }}
                  icon={<RocketOutlined />}
                >
                  Use Template
                </Button>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Empty State */}
      {filteredTemplates.length === 0 && (
        <div className="text-center py-12">
          <div className="text-5xl mb-4">🔍</div>
          <h3 className="text-xl font-bold text-primary mb-2">No templates found</h3>
          <p className="text-secondary">Try adjusting your search or filters</p>
        </div>
      )}

      {/* Template Details Modal */}
      <Modal
        open={selectedTemplate !== null}
        onCancel={() => setSelectedTemplate(null)}
        footer={null}
        width={700}
      >
        {selectedTemplate && (
          <div className="space-y-6 p-4">
            <div className="flex items-center gap-4">
              <div className="text-4xl text-accent">
                {categoryIcons[selectedTemplate.category] || <RocketOutlined />}
              </div>
              <div>
                <h2 className="text-2xl font-bold text-primary">{selectedTemplate.name}</h2>
                <div className="flex items-center gap-3 mt-2">
                  <Tag color={complexityColors[selectedTemplate.complexity]}>
                    {selectedTemplate.complexity.toUpperCase()} COMPLEXITY
                  </Tag>
                  <span className="text-secondary">
                    <TeamOutlined /> {selectedTemplate.agents_count} agents
                  </span>
                  <span className="text-secondary capitalize">
                    {selectedTemplate.category}
                  </span>
                </div>
              </div>
            </div>

            <div>
              <h3 className="font-bold text-primary mb-2">Description</h3>
              <p className="text-secondary">{selectedTemplate.description}</p>
            </div>

            <div>
              <h3 className="font-bold text-primary mb-2">Use Cases</h3>
              <div className="flex flex-wrap gap-2">
                {selectedTemplate.use_cases.map((useCase, idx) => (
                  <Tag key={idx}>{useCase}</Tag>
                ))}
              </div>
            </div>

            <div>
              <h3 className="font-bold text-primary mb-2">What's Included</h3>
              <ul className="list-disc list-inside space-y-1 text-secondary">
                <li>{selectedTemplate.agents_count} pre-configured agents</li>
                <li>Optimized workflow patterns</li>
                <li>Example prompts and tasks</li>
                <li>Best practices documentation</li>
              </ul>
            </div>

            <div className="flex gap-3">
              <Button
                type="primary"
                size="large"
                icon={<RocketOutlined />}
                onClick={() => handleUseTemplate(selectedTemplate)}
                block
              >
                Use This Template
              </Button>
              <Button size="large" onClick={() => setSelectedTemplate(null)}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default TemplateLibrary;
