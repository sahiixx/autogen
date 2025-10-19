import * as React from "react";
import Layout from "../components/layout";
import { graphql } from "gatsby";
import TemplateLibrary from "../components/views/templates/library";

// Templates page
const TemplatesPage = ({ data }: any) => {
  return (
    <Layout meta={data.site.siteMetadata} title="Templates" link={"/templates"}>
      <main style={{ height: "100%" }} className="h-full">
        <TemplateLibrary />
      </main>
    </Layout>
  );
};

export const query = graphql`
  query TemplatesPageQuery {
    site {
      siteMetadata {
        description
        title
      }
    }
  }
`;

export default TemplatesPage;
