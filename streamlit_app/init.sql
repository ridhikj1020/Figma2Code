-- Create wireframe_conversions table if it does not exist
-- Main wireframe conversions table
CREATE TABLE IF NOT EXISTS wireframe_conversions (
    id SERIAL PRIMARY KEY,

    -- Input data
    imagefilename VARCHAR(255) NOT NULL,
    image_data TEXT,  -- Base64 encoded image or URL
    fullprompt TEXT,  -- User's additional instructions

    -- Processing metadata
    complexity_level VARCHAR(20) CHECK (complexity_level IN ('Simple', 'Balanced', 'Complex')),
    framework VARCHAR(50) DEFAULT 'Next.js',
    input_mode VARCHAR(20) CHECK (input_mode IN ('upload', 'figma')),
    figma_file_id VARCHAR(100),

    -- Generated outputs
    htmlsnippet TEXT,
    nextjscomponent TEXT,
    tailwindclasses JSONB,  -- Changed to JSONB for better querying
    strapi_schema JSONB,    -- Strapi content type definitions

    -- AI analysis results
    rawairesponse JSONB,    -- Complete AI response with all analyses
    layout_analysis JSONB,  -- Separated for easier querying
    component_analysis JSONB,
    styling_analysis JSONB,
    content_analysis JSONB,

    -- Quality metrics
    validation_results JSONB,  -- Syntax checks, accessibility scores
    confidence_score DECIMAL(3,2),  -- 0.00 to 1.00
    processing_time_seconds INTEGER,

    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX idx_status ON wireframe_conversions(status);
CREATE INDEX idx_created_at ON wireframe_conversions(created_at DESC);
CREATE INDEX idx_complexity ON wireframe_conversions(complexity_level);
CREATE INDEX idx_user_id ON wireframe_conversions(user_id);

-- Full-text search on prompts
CREATE INDEX idx_fullprompt_search ON wireframe_conversions USING gin(to_tsvector('english', fullprompt));

-- User management table (optional, for multi-user support)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255),

    -- Subscription/usage tracking
    subscription_tier VARCHAR(20) DEFAULT 'free' CHECK (subscription_tier IN ('free', 'pro', 'enterprise')),
    monthly_conversions_used INTEGER DEFAULT 0,
    monthly_conversion_limit INTEGER DEFAULT 10,

    -- Preferences
    default_framework VARCHAR(50) DEFAULT 'Next.js',
    default_complexity VARCHAR(20) DEFAULT 'Balanced',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Add user_id foreign key to wireframe_conversions
ALTER TABLE wireframe_conversions
ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;

-- Processing logs table (for debugging and monitoring)
CREATE TABLE IF NOT EXISTS processing_logs (
    id SERIAL PRIMARY KEY,
    conversion_id INTEGER REFERENCES wireframe_conversions(id) ON DELETE CASCADE,

    step_name VARCHAR(100) NOT NULL,  -- 'layout_analysis', 'code_generation', etc.
    model_used VARCHAR(50),

    input_data JSONB,
    output_data JSONB,

    execution_time_ms INTEGER,
    tokens_used INTEGER,

    status VARCHAR(20) CHECK (status IN ('success', 'error', 'warning')),
    error_details TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_processing_logs_conversion ON processing_logs(conversion_id);
CREATE INDEX idx_processing_logs_status ON processing_logs(status);

-- Component library table (reusable components detected)
CREATE TABLE IF NOT EXISTS detected_components (
    id SERIAL PRIMARY KEY,
    conversion_id INTEGER REFERENCES wireframe_conversions(id) ON DELETE CASCADE,

    component_type VARCHAR(100) NOT NULL,  -- 'button', 'card', 'navbar', etc.
    component_name VARCHAR(255),

    properties JSONB,  -- Component props/attributes
    code_snippet TEXT,

    reuse_count INTEGER DEFAULT 1,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_components_type ON detected_components(component_type);

-- Feedback table (for quality improvement)
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    conversion_id INTEGER REFERENCES wireframe_conversions(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,

    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,

    helpful_features TEXT[],  -- Array of what worked well
    issues_found TEXT[],      -- Array of problems encountered

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
