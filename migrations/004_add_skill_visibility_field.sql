-- Migration: 004_add_skill_visibility_field.sql
-- Add skill_visibility JSONB field to portfolio_items table

-- First, check if the column already exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'portfolio_items' AND column_name = 'skill_visibility'
    ) THEN
        -- Add the skill_visibility column
        ALTER TABLE portfolio_items ADD COLUMN skill_visibility JSONB DEFAULT '{}'::jsonb;

        -- Create index for the new column
        CREATE INDEX IF NOT EXISTS idx_portfolio_items_skill_visibility ON portfolio_items USING GIN(skill_visibility);
        
        -- Initialize skill_visibility from existing skills
        -- For each item, create a JSON object with each skill as key and true as value
        UPDATE portfolio_items
        SET skill_visibility = (
            SELECT jsonb_object_agg(skill, true)
            FROM jsonb_array_elements_text(skills) AS skill
        )
        WHERE skills IS NOT NULL AND skills != '[]'::jsonb;
    END IF;
END $$;
