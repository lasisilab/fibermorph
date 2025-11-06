# Deploying fibermorph GUI to Streamlit Cloud

This guide explains how to deploy the fibermorph Streamlit GUI to Streamlit Cloud.

## Prerequisites

1. A GitHub account
2. A Streamlit Cloud account (free tier available at [share.streamlit.io](https://share.streamlit.io))

## Deployment Steps

### Option 1: Deploy from this branch

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Select your repository: `lasisilab/fibermorph`
4. Select branch: `feature/streamlit-gui`
5. Set main file path: `streamlit_app.py`
6. Click "Deploy"

### Option 2: Deploy from your fork

1. Fork the `lasisilab/fibermorph` repository to your GitHub account
2. Make sure you're on the `feature/streamlit-gui` branch
3. Go to [share.streamlit.io](https://share.streamlit.io)
4. Click "New app"
5. Select your forked repository
6. Select branch: `feature/streamlit-gui`
7. Set main file path: `streamlit_app.py`
8. Click "Deploy"

## Configuration Files

The following files are configured for Streamlit Cloud deployment:

- **`streamlit_app.py`**: Entry point for Streamlit Cloud
- **`requirements.txt`**: Python dependencies
- **`.python-version`**: Specifies Python 3.11
- **`.streamlit/config.toml`**: App configuration (theme, upload limits, etc.)
- **`packages.txt`**: System-level dependencies for image processing

## Features

Once deployed, the app will allow users to:

- Upload TIFF images or provide a URL to download images
- Choose between Curvature and Section analysis workflows
- Configure analysis parameters (resolution, window size, etc.)
- View results in an interactive table
- Download results as CSV
- Download full output bundle as ZIP

## Limitations

- Maximum upload size: 500 MB (configured in `.streamlit/config.toml`)
- Python version: 3.10+ required (due to Streamlit dependencies)
- Processing time depends on image count and Streamlit Cloud resources

## Troubleshooting

### Deployment fails

- Check that all files are committed and pushed to the branch
- Verify Python version compatibility (3.10+)
- Check Streamlit Cloud logs for specific error messages

### Import errors

- Ensure all dependencies are listed in `requirements.txt`
- System dependencies should be in `packages.txt`

### Performance issues

- Consider using Streamlit Cloud's paid tiers for more resources
- Reduce the number of parallel jobs in analysis settings
- Process images in smaller batches

## Local Testing

Before deploying, you can test the app locally:

```bash
# Install with GUI extras
pip install -e ".[gui]"

# Run the app
streamlit run streamlit_app.py
```

Or use the convenience command:

```bash
fibermorph-gui
```

## Support

For issues related to:
- **Deployment**: Check Streamlit Cloud documentation
- **fibermorph functionality**: Open an issue on GitHub
- **GUI features**: Open an issue on GitHub with "GUI" label
