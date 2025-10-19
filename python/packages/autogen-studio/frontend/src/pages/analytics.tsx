import * as React from "react";
import Layout from "../components/layout";
import { graphql } from "gatsby";
import AnalyticsDashboard from "../components/views/analytics/dashboard";

// Analytics page
const AnalyticsPage = ({ data }: any) => {
  return (
    <Layout meta={data.site.siteMetadata} title="Analytics" link={"/analytics"}>
      <main style={{ height: "100%" }} className="h-full">
        <AnalyticsDashboard />
      </main>
    </Layout>
  );
};

export const query = graphql`
  query AnalyticsPageQuery {
    site {
      siteMetadata {
        description
        title
      }
    }
  }
`;

export default AnalyticsPage;
