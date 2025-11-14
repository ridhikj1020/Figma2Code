import streamlit as st
import requests
import time
from PIL import Image
import json

# Page config
st.set_page_config(
    page_title="Figma2Code - AI Wireframe Converter",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ✅ CRITICAL: Initialize ALL session state variables BEFORE any widgets
if 'generated_code' not in st.session_state:
    st.session_state.generated_code = None
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'preview_html' not in st.session_state:
    st.session_state.preview_html = None
# ✅ Initialize user_prompt explicitly BEFORE the text_area widget
if 'user_prompt' not in st.session_state:
    st.session_state.user_prompt = ""

# Custom CSS (keep as is)
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        color: white;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .upload-box {
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        background: #f8f9ff;
    }
    .status-box {
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .status-processing {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
    }
    .status-success {
        background: #d4edda;
        border-left: 4px solid #28a745;
    }
    .status-error {
        background: #f8d7da;
        border-left: 4px solid #dc3545;
    }
    .code-preview {
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 1rem;
        border-radius: 8px;
        font-family: 'Monaco', 'Courier New', monospace;
        font-size: 0.9rem;
        max-height: 500px;
        overflow-y: auto;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1.1rem;
        border-radius: 8px;
        font-weight: 600;
    }
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# N8N Webhook URL
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/6e5bd044-e0bb-4b58-9cd1-03a221804357"


def process_wireframe(image_file, user_prompt):
    """Send wireframe to n8n workflow and get generated code"""
    try:
        # Read image file
        image_bytes = image_file.read()

        # Prepare multipart form data
        files = {
            'image': (image_file.name, image_bytes, image_file.type)
        }
        data = {
            'userprompt': user_prompt
        }

        # Send request to n8n with a much longer timeout (15 minutes for the entire workflow)
        # n8n configured to respond "When Last Node Finishes" with merge nodes before code gen
        response = requests.post(
            N8N_WEBHOOK_URL,
            files=files,
            data=data,
            timeout=1500  # 25 minutes - allow enough time for AI models to process
        )

        if response.status_code == 200:
            # Try to parse JSON response from Node G
            try:
                json_response = response.json()

                # Node G returns an array of items, get the first one
                if isinstance(json_response, list) and len(json_response) > 0:
                    # Extract the json object from the first item
                    data_obj = json_response[0].get('json', json_response[0])
                elif isinstance(json_response, dict):
                    # If it's already a dict, use it directly
                    data_obj = json_response.get('json', json_response)
                else:
                    return None, f"Unexpected response format: {type(json_response)}"

                # Extract HTML from the response structure
                html_code = data_obj.get('html', '')

                # ✅ Simplified validation - now that merge nodes are in place,
                # just check for substantial HTML content
                if html_code and len(html_code) > 500:
                    return html_code, None
                else:
                    # Still incomplete - show detailed error for debugging
                    react_code = data_obj.get('react', '')
                    tailwind_data = data_obj.get('tailwind', {})
                    validation = data_obj.get('validation', {})

                    error_details = {
                        'html_length': len(html_code),
                        'react_length': len(react_code),
                        'tailwind_keys': len(tailwind_data) if isinstance(tailwind_data, dict) else 0,
                        'validation': validation
                    }
                    return None, f"⚠️ Received response but HTML is incomplete. Details:\n{json.dumps(error_details, indent=2)}\n\nFirst 200 chars of HTML: {html_code[:200]}"

            except json.JSONDecodeError:
                # If not JSON, treat as plain text/HTML
                result = response.text
                if len(result) < 500:
                    return None, f"Received incomplete response ({len(result)} chars). Response: {result[:200]}..."
                return result, None
        else:
            return None, f"Error: {response.status_code} - {response.text}"

    except requests.exceptions.Timeout:
        return None, "The workflow is taking longer than 15 minutes. Please check n8n workflow status manually."
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to n8n. Please ensure n8n is running and accessible."
    except Exception as e:
        return None, f"Error: {str(e)}"


def start_workflow_async(image_file, user_prompt):
    """Start the n8n workflow asynchronously and return execution ID"""
    try:
        # Read image file
        image_bytes = image_file.read()

        # Prepare multipart form data
        files = {
            'image': (image_file.name, image_bytes, image_file.type)
        }
        data = {
            'userprompt': user_prompt,
            'async': 'true'
        }

        # Send request to start workflow
        response = requests.post(
            N8N_WEBHOOK_URL,
            files=files,
            data=data,
            timeout=30
        )

        if response.status_code == 202:
            return response.json().get('executionId'), None
        elif response.status_code == 200:
            return response.text, None
        else:
            return None, f"Error: {response.status_code} - {response.text}"

    except requests.exceptions.Timeout:
        return None, "Timeout starting workflow"
    except Exception as e:
        return None, f"Error: {str(e)}"


def check_workflow_status(execution_id):
    """Check the status of a running n8n workflow"""
    try:
        status_url = f"http://n8n:5678/api/v1/executions/{execution_id}"
        response = requests.get(status_url, timeout=10)

        if response.status_code == 200:
            execution = response.json()
            status = execution.get('finished', False)
            if status:
                return execution.get('data', {}).get('resultData', 'Workflow completed'), None, True
            else:
                return None, None, False
        else:
            return None, f"Status check failed: {response.status_code}", False

    except Exception as e:
        return None, f"Status check error: {str(e)}", False


# Header
st.markdown('<h1 class="main-header">🎨 Figma2Code</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Transform wireframes into production-ready code using AI</p>',
            unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    st.markdown("#### 🤖 AI Models Used")
    st.info("""
    **Image Analysis:**
    - Layout: llava:7b
    - Components: llava:13b
    - Styling: llava:7b
    - Content: llava:13b

    **Code Generation:**
    - HTML: codellama:13b
    - React: codellama:13b
    - Tailwind: codellama:7b
    """)

    st.markdown("#### ⏱️ Processing Time")
    st.metric("Expected Duration", "~10 min", "±2 min")

    st.markdown("#### 📊 Workflow Status")
    if st.session_state.processing:
        st.warning("🔄 Processing...")
    else:
        st.success("✅ Ready")



    st.markdown("---")
    st.caption("Built with ❤️ using Streamlit + n8n + Ollama")

# Main content area
tab1, tab2, tab3 = st.tabs(["🎨 Generate", "📊 Results", "📖 Guide"])

with tab1:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 📤 Upload Wireframe")

        uploaded_file = st.file_uploader(
            "Choose a wireframe image",
            type=['png', 'jpg', 'jpeg', 'gif', 'webp'],
            help="Upload your Figma wireframe or any UI mockup"
        )

        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Wireframe", use_column_width=True)
            st.caption(f"📏 Size: {image.size[0]}x{image.size[1]} | 📦 Format: {image.format}")

    with col2:
        st.markdown("### 💬 Instructions (Optional)")

        # ✅ FIXED: Don't use both 'value' and 'key' together - just use 'key'
        st.text_area(
            "Additional requirements",
            placeholder="e.g., Make it modern with dark mode support, use card layout, add animations...",
            height=150,
            help="Provide specific instructions for the AI models",
            key="user_prompt"  # ✅ This automatically manages st.session_state.user_prompt
        )

        st.markdown("### 🎯 Quick Presets")
        preset_col1, preset_col2 = st.columns(2)

        with preset_col1:
            # ✅ Now these buttons can safely write to st.session_state.user_prompt
            if st.button("🌙 Dark Mode", use_container_width=True, key="dark_mode_btn"):
                st.session_state.user_prompt = "Make it modern with dark mode, use dark backgrounds and light text"
                st.rerun()
            if st.button("🎴 Card Layout", use_container_width=True, key="card_layout_btn"):
                st.session_state.user_prompt = "Use card-based layout with shadows and rounded corners"
                st.rerun()

        with preset_col2:
            if st.button("✨ Minimal", use_container_width=True, key="minimal_btn"):
                st.session_state.user_prompt = "Keep it minimal and clean, lots of whitespace, simple colors"
                st.rerun()
            if st.button("🎨 Colorful", use_container_width=True, key="colorful_btn"):
                st.session_state.user_prompt = "Use vibrant colors, gradients, and modern UI trends"
                st.rerun()

    st.markdown("---")

    # Generate button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        generate_button = st.button(
            "🚀 Generate Code",
            use_container_width=True,
            disabled=not uploaded_file or st.session_state.processing,
            key="generate_btn"
        )

    if generate_button and uploaded_file:
        st.session_state.processing = True
        st.session_state.generated_code = None
        st.session_state.preview_html = None

        # Progress tracking
        progress_container = st.container()

        with progress_container:
            st.markdown('<div class="status-box status-processing">', unsafe_allow_html=True)
            st.markdown("### 🔄 Processing Your Wireframe")

            progress_bar = st.progress(0)
            status_text = st.empty()

            # Reset file pointer
            uploaded_file.seek(0)

            # ✅ Safely get user_prompt with fallback to empty string
            user_prompt = st.session_state.get('user_prompt', '')

            # Make the API call in background thread
            import threading

            result_container = {"result": None, "error": None, "completed": False}

            def make_api_call():
                try:
                    result, error = process_wireframe(uploaded_file, user_prompt)
                    result_container["result"] = result
                    result_container["error"] = error
                except Exception as e:
                    result_container["error"] = str(e)
                finally:
                    result_container["completed"] = True

            # Start the API call in background
            status_text.text("📤 Uploading image to n8n...")
            progress_bar.progress(0.05)
            api_thread = threading.Thread(target=make_api_call)
            api_thread.start()

            # Wait a bit for the upload to start
            time.sleep(2)

            # Show realistic progress while waiting for the actual workflow to complete
            # Since we know it takes ~7-8 minutes, we'll show progress over that time
            stages = [
                (0.10, "🔗 Workflow started..."),
                (0.15, "🔍 Analyzing layout with llava:7b... (1-2 min)"),                (0.25, "🧩 Detecting components with llava:13b... (1-2 min)"),
                (0.35, "🎨 Extracting styling with llava:7b... (1-2 min)"),
                (0.45, "📝 Analyzing content with llava:13b... (1-2 min)"),
                (0.55, "🔗 Aggregating analysis results..."),
                (0.60, "💻 Generating HTML with codellama:13b... (1-2 min)"),
                (0.70, "⚛️ Creating React component with codellama:13b... (1-2 min)"),
                (0.80, "🎨 Generating Tailwind classes with codellama:7b... (30-60 sec)"),
                (0.90, "📦 Building final output..."),
            ]

            # Show progress updates every 45 seconds (realistic for 7-8 min workflow)
            stage_index = 0
            update_interval = 45  # seconds between updates

            while not result_container["completed"]:
                if stage_index < len(stages):
                    progress, message = stages[stage_index]
                    progress_bar.progress(progress)
                    status_text.text(message)
                    stage_index += 1

                    # Check every 5 seconds if completed, but only update UI every 45 seconds
                    for _ in range(int(update_interval / 5)):
                        time.sleep(5)
                        if result_container["completed"]:
                            break
                else:
                    # After all stages, keep checking but show waiting message
                    progress_bar.progress(0.95)
                    status_text.text("⏳ Finalizing and packaging results...")
                    time.sleep(10)

            # Wait for thread to fully complete
            api_thread.join(timeout=10)

            # Now display the final result
            if result_container["completed"]:
                progress_bar.progress(1.0)
                status_text.text("✅ Processing complete!")
                time.sleep(1)  # Brief pause to show completion
                st.markdown('</div>', unsafe_allow_html=True)

                if result_container["error"]:
                    st.markdown('<div class="status-box status-error">', unsafe_allow_html=True)
                    st.error(f"❌ {result_container['error']}")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    # ✅ Only save and display if we have actual results
                    if result_container["result"] and len(result_container["result"]) > 100:
                        st.session_state.preview_html = result_container["result"]
                        st.session_state.generated_code = {
                            'html': result_container["result"],
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                        }
                        st.markdown('<div class="status-box status-success">', unsafe_allow_html=True)
                        st.success("✅ Code generated successfully!")
                        st.info(f"📊 Generated {len(result_container['result'])} characters of code")
                        st.markdown('</div>', unsafe_allow_html=True)
                        st.balloons()
                    else:
                        st.markdown('<div class="status-box status-error">', unsafe_allow_html=True)
                        st.warning("⚠️ Received incomplete response from n8n. The workflow may still be running.")
                        st.info("💡 Please check the n8n workflow execution logs at http://localhost:5678")
                        st.markdown('</div>', unsafe_allow_html=True)
            else:
                progress_bar.progress(0.5)
                status_text.text("⚠️ Timeout waiting for workflow...")
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('<div class="status-box status-error">', unsafe_allow_html=True)
                st.error("❌ The request timed out. Please check n8n workflow status.")
                st.markdown('</div>', unsafe_allow_html=True)

        st.session_state.processing = False

with tab2:
    st.markdown("### 📊 Generated Results")

    if st.session_state.generated_code:
        result_tabs = st.tabs(["🖼️ Preview", "⚛️ React", "🎨 Tailwind", "📦 Strapi", "📥 Download"])

        with result_tabs[0]:
            st.markdown("#### Live Preview")
            if st.session_state.preview_html:
                st.components.v1.html(st.session_state.preview_html, height=800, scrolling=True)

        with result_tabs[1]:
            st.markdown("#### React Component")
            st.code("""
// Extracted React component will appear here
import React from 'react';

export default function GeneratedPage({ strapiData }) {
  return (
    <div className="container mx-auto">
      {/* Generated component */}
    </div>
  );
}
            """, language="typescript")

        with result_tabs[2]:
            st.markdown("#### Tailwind Classes")
            st.json({
                "container": ["mx-auto", "px-4", "max-w-7xl"],
                "header": ["bg-white", "shadow-md", "py-4"],
                "button": ["bg-blue-600", "hover:bg-blue-700", "text-white", "px-6", "py-3", "rounded-lg"]
            })

        with result_tabs[3]:
            st.markdown("#### Strapi Schema")
            st.json({
                "kind": "collectionType",
                "collectionName": "pages",
                "info": {
                    "singularName": "page",
                    "pluralName": "pages",
                    "displayName": "Page"
                },
                "attributes": {
                    "title": {"type": "string", "required": True},
                    "description": {"type": "text"}
                }
            })

        with result_tabs[4]:
            st.markdown("#### Download Package")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.download_button(
                    "📄 Download HTML",
                    st.session_state.preview_html or "",
                    "generated-page.html",
                    "text/html",
                    use_container_width=True,
                    key="download_html_btn"
                )

            with col2:
                st.download_button(
                    "⚛️ Download React",
                    "// React component code",
                    "GeneratedPage.tsx",
                    "text/typescript",
                    use_container_width=True,
                    key="download_react_btn"
                )

            with col3:
                st.download_button(
                    "📦 Download All",
                    json.dumps(st.session_state.generated_code, indent=2),
                    "figma2code-package.json",
                    "application/json",
                    use_container_width=True,
                    key="download_all_btn"
                )

            st.info("💡 **Pro Tip:** Import these files into your Next.js project and connect to Strapi CMS!")

    else:
        st.info("👆 Generate code from the 'Generate' tab first!")

with tab3:
    st.markdown("### 📖 How to Use")

    st.markdown("""
    #### Step 1: Prepare Your Wireframe
    - Export your Figma design as PNG/JPG
    - Ensure text is readable
    - Keep the layout clear and organized

    #### Step 2: Upload & Configure
    - Upload your wireframe image
    - (Optional) Add specific instructions
    - Click "Generate Code"

    #### Step 3: Wait for Processing
    The AI will analyze your wireframe through multiple stages:
    1. 🔍 Layout analysis
    2. 🧩 Component detection
    3. 🎨 Styling extraction
    4. 📝 Content mapping
    5. 💻 HTML generation
    6. ⚛️ React creation
    7. 🎨 Tailwind styling
    8. 📦 Strapi schema

    #### Step 4: Review & Download
    - Preview the generated page
    - Download individual files or complete package
    - Integrate into your project

    ---

    ### 🎯 Best Practices

    - ✅ Use high-resolution wireframes (1920x1080+)
    - ✅ Keep layouts simple and well-structured
    - ✅ Label sections clearly in Figma
    - ✅ Use consistent spacing
    - ❌ Avoid overly complex nested components
    - ❌ Don't include too much text in one screen

    ---

    ### 🔧 Technical Details

    **Models Used:**
    - Vision: LLaVA 7B & 13B
    - Code: CodeLlama 7B & 13B 

    **Processing Time:**
    - Image Analysis: ~7-8 minutes
    - Code Generation: ~8-10 minutes
    - Total: ~15-20 minutes

    **Output Formats:**
    - Next.js 14 React components (TypeScript)
    - Tailwind CSS utility classes
    - Strapi v4 content schemas
    - Semantic HTML5
    """)

    st.markdown("---")

    st.markdown("### 🐛 Troubleshooting")

    with st.expander("⚠️ Processing takes too long"):
        st.markdown("""
        - Check if Ollama is running: `ollama list`
        - Verify models are downloaded
        - Check n8n workflow is active
        - Reduce image size if > 5MB
        - Be patient - AI model inference takes 15-20 minutes
        """)

    with st.expander("❌ Generation fails"):
        st.markdown("""
        - Ensure n8n webhook URL is correct
        - Check Ollama API is accessible
        - Verify all models are pulled
        - Check Docker container logs
        """)

    with st.expander("🖼️ Preview doesn't look right"):
        st.markdown("""
        - Generated code might need manual tweaking
        - Try adding more specific instructions
        - Simplify your wireframe layout
        - Adjust Tailwind classes manually
        """)

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("🤖 Models", "7", "Active")

with col2:
    st.metric("⚡ Avg Time", "10 min", "±2 min")

with col3:
    if st.session_state.generated_code:
        st.metric("✅ Status", "Complete", "Ready")
    else:
        st.metric("⏳ Status", "Waiting", "Upload file")