import json
import matplotlib.pyplot as plt
import numpy as np

data_path = r'd:\PROJECTS\MindTrace-AI-\models_evaluation_summary.json'
output_path = r'd:\PROJECTS\MindTrace-AI-\confusion_matrix_screenshot.png'

with open(data_path, 'r') as f:
    data = json.load(f)

cm = np.array(data['confusion_matrix'])
labels = [l.capitalize() for l in data['labels']]

fig, ax = plt.subplots(figsize=(8, 8))
cax = ax.matshow(cm, cmap='Blues')
plt.title('Emotion Detection Model - Confusion Matrix', pad=20, fontsize=16)

fig.colorbar(cax)

ax.set_xticks(np.arange(len(labels)))
ax.set_yticks(np.arange(len(labels)))
ax.set_xticklabels(labels, fontsize=12)
ax.set_yticklabels(labels, fontsize=12)

plt.xlabel('Predicted Emotion', fontsize=14, labelpad=10)
plt.ylabel('True Emotion', fontsize=14, labelpad=10)
ax.xaxis.set_ticks_position('bottom')

for i in range(len(labels)):
    for j in range(len(labels)):
        ax.text(j, i, str(cm[i, j]), va='center', ha='center', fontsize=14,
                color="white" if cm[i, j] > (cm.max() / 2) else "black")

plt.tight_layout()
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Plot saved successfully to {output_path}")
