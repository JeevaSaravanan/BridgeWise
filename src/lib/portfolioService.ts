import Database from './database';
import { PortfolioItem, PortfolioData } from './portfolioStorage';

export class PortfolioService {
  // Get all portfolio items
  static async getAllItems(): Promise<PortfolioItem[]> {
    try {
      const result = await Database.query(`
        SELECT 
          id,
          title,
          type,
          url,
          summary,
          skills,
          thumbnail,
          analysis_result,
          created_at as "createdAt",
          updated_at as "updatedAt"
        FROM portfolio_items 
        ORDER BY created_at DESC
      `);

      return result.rows.map(row => ({
        ...row,
        id: row.id, // Keep as UUID string
        skills: Array.isArray(row.skills) ? row.skills : []
      }));
    } catch (error) {
      console.error('Error fetching portfolio items:', error);
      throw error;
    }
  }

  // Create new portfolio item
  static async createItem(item: Omit<PortfolioItem, 'id'>): Promise<PortfolioItem> {
    try {
      const result = await Database.query(`
        INSERT INTO portfolio_items (title, type, url, summary, skills, thumbnail, analysis_result)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING 
          id,
          title,
          type,
          url,
          summary,
          skills,
          thumbnail,
          analysis_result,
          created_at as "createdAt",
          updated_at as "updatedAt"
      `, [
        item.title,
        item.type,
        item.url || null,
        item.summary,
        JSON.stringify(item.skills || []),
        item.thumbnail || '📄',
        item.analysisResult ? JSON.stringify(item.analysisResult) : null
      ]);

      const newItem = result.rows[0];
      return {
        ...newItem,
        id: newItem.id, // Keep as UUID string
        skills: Array.isArray(newItem.skills) ? newItem.skills : []
      };
    } catch (error) {
      console.error('Error creating portfolio item:', error);
      throw error;
    }
  }

  // Update existing portfolio item
  static async updateItem(id: string, updates: Partial<PortfolioItem>): Promise<PortfolioItem | null> {
    try {
      const setParts = [];
      const values = [];
      let valueIndex = 1;

      if (updates.title !== undefined) {
        setParts.push(`title = $${valueIndex++}`);
        values.push(updates.title);
      }
      if (updates.summary !== undefined) {
        setParts.push(`summary = $${valueIndex++}`);
        values.push(updates.summary);
      }
      if (updates.skills !== undefined) {
        setParts.push(`skills = $${valueIndex++}`);
        values.push(JSON.stringify(updates.skills));
      }
      if (updates.url !== undefined) {
        setParts.push(`url = $${valueIndex++}`);
        values.push(updates.url);
      }
      if (updates.analysisResult !== undefined) {
        setParts.push(`analysis_result = $${valueIndex++}`);
        values.push(JSON.stringify(updates.analysisResult));
      }
      if (setParts.length === 0) {
        throw new Error('No valid updates provided');
      }

      values.push(id); // Use UUID string directly

      const result = await Database.query(`
        UPDATE portfolio_items 
        SET ${setParts.join(', ')}, updated_at = CURRENT_TIMESTAMP
        WHERE id = $${valueIndex}
        RETURNING 
          id,
          title,
          type,
          url,
          summary,
          skills,
          thumbnail,
          analysis_result,
          created_at as "createdAt",
          updated_at as "updatedAt"
      `, values);

      if (result.rows.length === 0) {
        return null;
      }

      const updatedItem = result.rows[0];
      return {
        ...updatedItem,
        id: updatedItem.id, // Keep as UUID string
        skills: Array.isArray(updatedItem.skills) ? updatedItem.skills : []
      };
    } catch (error) {
      console.error('Error updating portfolio item:', error);
      throw error;
    }
  }

  // Delete portfolio item
  static async deleteItem(id: string): Promise<boolean> {
    try {
      const result = await Database.query(
        'DELETE FROM portfolio_items WHERE id = $1',
        [id] // Use UUID string directly
      );
      return result.rowCount > 0;
    } catch (error) {
      console.error('Error deleting portfolio item:', error);
      throw error;
    }
  }

  // Get portfolio statistics
  static async getStats() {
    try {
      const [countResult, skillsResult, typesResult] = await Promise.all([
        Database.query('SELECT COUNT(*) as total FROM portfolio_items'),
        Database.query(`
          SELECT DISTINCT jsonb_array_elements_text(skills) as skill 
          FROM portfolio_items 
          WHERE skills IS NOT NULL
        `),
        Database.query(`
          SELECT type, COUNT(*) as count 
          FROM portfolio_items 
          GROUP BY type
        `)
      ]);

      const totalItems = parseInt(countResult.rows[0]?.total || '0');
      const uniqueSkills = skillsResult.rows.map(row => row.skill);
      const typeBreakdown = typesResult.rows.reduce((acc, row) => {
        acc[row.type] = parseInt(row.count);
        return acc;
      }, {} as Record<string, number>);

      return {
        totalItems,
        skillCount: uniqueSkills.length,
        typeBreakdown,
        uniqueSkills
      };
    } catch (error) {
      console.error('Error getting portfolio stats:', error);
      return {
        totalItems: 0,
        skillCount: 0,
        typeBreakdown: {},
        uniqueSkills: []
      };
    }
  }

  // Search portfolio items
  static async searchItems(query: string): Promise<PortfolioItem[]> {
    try {
      const result = await Database.query(`
        SELECT 
          id,
          title,
          type,
          url,
          summary,
          skills,
          thumbnail,
          analysis_result,
          created_at as "createdAt",
          updated_at as "updatedAt"
        FROM portfolio_items 
        WHERE 
          title ILIKE $1 
          OR summary ILIKE $1 
          OR skills::text ILIKE $1
        ORDER BY created_at DESC
      `, [`%${query}%`]);

      return result.rows.map(row => ({
        ...row,
        id: parseInt(row.id),
        skills: Array.isArray(row.skills) ? row.skills : []
      }));
    } catch (error) {
      console.error('Error searching portfolio items:', error);
      throw error;
    }
  }

  // Seed database with sample data
  static async seedSampleData(): Promise<void> {
    try {
      const sampleItems = [
        {
          title: "React Dashboard Project",
          type: "github" as const,
          url: "https://github.com/user/react-dashboard",
          summary: "A comprehensive analytics dashboard built with React, TypeScript, and D3.js featuring real-time data visualization and user management.",
          skills: ["React", "TypeScript", "D3.js", "API Design"],
          thumbnail: "📊",
          createdAt: new Date().toISOString()
        },
        {
          title: "Product Strategy Deck",
          type: "file" as const,
          summary: "Strategic roadmap for launching a new mobile product feature, including market analysis, user personas, and go-to-market strategy.",
          skills: ["Product Strategy", "Market Analysis", "User Research"],
          thumbnail: "📋",
          createdAt: new Date().toISOString()
        },
        {
          title: "ML Model Documentation",
          type: "url" as const,
          url: "https://docs.example.com/ml-model",
          summary: "Complete documentation for a machine learning model that predicts customer churn with 89% accuracy using Python and scikit-learn.",
          skills: ["Machine Learning", "Python", "Data Analysis"],
          thumbnail: "🤖",
          createdAt: new Date().toISOString()
        }
      ];

      for (const item of sampleItems) {
        await this.createItem(item);
      }

      console.log('✅ Sample portfolio data seeded successfully');
    } catch (error) {
      console.error('Error seeding sample data:', error);
      throw error;
    }
  }
}
