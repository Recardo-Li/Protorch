from pathlib import Path
import sys

sys.path.append(".")
from sklearn.metrics import confusion_matrix
import numpy as np
import pandas as pd
import json
import argparse
import data.globalvar as globalvar
from data.data_pipeline import DataPipeline
from data.raw_input import UserInput
from prompts.generate_query_tool import convert_json_format, query_single_tool_for_caller
from utils.seed import setup_seed
from utils.module_loader import *
from config import *
from fairscale.nn.model_parallel.initialize import initialize_model_parallel
import os
import matplotlib.pyplot as plt

def plot_confusion_matrix(cm, labels, title, accuracy, output_path):
    """
    plot confusion matrix and save as jpg

    :param cm: confusion matrix (numpy array)
    :param labels: class labels (list)
    :param title
    :param accuracy
    :param output_path
    """
    plt.figure(figsize=(10, 8))
    plt.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    plt.title(f"{title}\nAccuracy: {accuracy:.2f}%", fontsize=14)
    plt.colorbar()

    tick_marks = np.arange(len(labels))
    plt.xticks(tick_marks, labels, rotation=45, ha="right")
    plt.yticks(tick_marks, labels)

 
    for i in range(len(cm)):
        for j in range(len(cm[i])):
            plt.text(j, i, format(cm[i, j], "d"), ha="center", va="center", color="black")

    plt.ylabel("True Label")
    plt.xlabel("Predicted Label")
    plt.tight_layout()
    plt.savefig(output_path, format="jpg")
    plt.close()



def run(config):
    input_file_name = os.path.splitext(os.path.basename(config.data.input))[0]
    result = []
    cnt = 1
    tool_correct = 0  # Count of correct tool selections
    category_correct = 0  # Count of correct category selections
    total = 0  # Total number of questions
    wrong_category_cases = []  # Store cases where category selection is wrong
    wrong_tool_cases = []  # Store cases where tool selection is wrong

    # For confusion matrix
    true_tool_labels = []
    predicted_tool_labels = []
    true_category_labels = []
    predicted_category_labels = []
    toolset = load_toolset(config.toolset)
    selector = load_selector(config.selector, toolset)
    data_pipeline = DataPipeline(toolset, selector, config.caller_root)

    first_input_element = UserInput(config.data.input).raw_inputs[0]
    true_tool_name = first_input_element.values["tool"]
    true_category_name = first_input_element.values["category"]

    for raw_input in UserInput(config.data.input).raw_inputs:
        print(f"Processing {cnt}th question")
        cnt += 1
        total += 1
        data_pipeline.process_select(raw_input)
        selected_category = data_pipeline.selection[0]
        selected_tool = data_pipeline.selection[1]
        question = raw_input.values["question"]

       # Append labels for confusion matrix
        true_category_labels.append(raw_input.values["category"])
        predicted_category_labels.append(selected_category)
        true_tool_labels.append(raw_input.values["tool"])
        predicted_tool_labels.append(selected_tool)

        

        result.append(
            {
                "question": question,
                "tool": selected_tool,
                "category": selected_category,
            }
        )

        # Check if category selection is correct
        if selected_category == raw_input.values["category"]:
            category_correct += 1
            print(f"\033[32m{selected_category} is correctly selected\033[0m")
        else:
            print(f"\033[31m{selected_category} is incorrectly selected\033[0m")
            # Save cases where category selection is wrong
            wrong_category_cases.append({
                "question": question,
                "selected_category": selected_category,
                "correct_category": raw_input.values["category"]
            })

        # Check if tool selection is correct
        if selected_tool == raw_input.values["tool"]:
            tool_correct += 1
            print(f"\033[32m{selected_tool} is correctly selected\033[0m")
        else:
            print(f"\033[31m{selected_tool} is incorrectly selected\033[0m")
            # Save cases where tool selection is wrong
            wrong_tool_cases.append({
                "question": question,
                "selected_tool": selected_tool,
                "correct_tool": raw_input.values["tool"]
            })

        print(f"Finished processing {cnt}th question")

    # Calculate accuracy
    tool_accuracy = tool_correct / total * 100
    category_accuracy = category_correct / total * 100

    print(f"\nTool selection accuracy: {tool_accuracy:.2f}%")
    print(f"Category selection accuracy: {category_accuracy:.2f}%\n")

    input_file_name_with_count = f"{input_file_name}_{total}_queries"

    # Save results
    output_dir = os.path.dirname(config.data.output)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    json.dump(result, open(config.data.output, "w"), indent=4)

    # Create the directory for storing wrong selections
    error_output_dir = os.path.join(output_dir, "selector_test_details")
    if not os.path.exists(error_output_dir):
        os.makedirs(error_output_dir)

    # Save wrong category selection cases to a CSV file
    if wrong_category_cases:
        wrong_category_df = pd.DataFrame(wrong_category_cases)
        wrong_category_df.to_csv(os.path.join(error_output_dir, "wrong_category.csv"), index=False)

    # Save wrong tool selection cases to a CSV file
    if wrong_tool_cases:
        wrong_tool_df = pd.DataFrame(wrong_tool_cases)
        wrong_tool_df.to_csv(os.path.join(error_output_dir, "wrong_tool.csv"), index=False)


   

    # 过滤掉 true_tool_labels 中为 None 的元素，同时同步过滤 predicted_tool_labels
    true_tool_labels, predicted_tool_labels = zip(*[
        (true, pred) for true, pred in zip(true_tool_labels, predicted_tool_labels) if true is not None
    ])

    # 转换回列表（因为 zip 返回的是元组）
    true_tool_labels = list(true_tool_labels)
    predicted_tool_labels = list(predicted_tool_labels)

    # same for category prediction
    true_category_labels, predicted_category_labels = zip(*[
        (true, pred) for true, pred in zip(true_category_labels, predicted_category_labels) if true is not None
    ])

    # 转换回列表（因为 zip 返回的是元组）
    true_tool_labels = list(true_tool_labels)
    predicted_tool_labels = list(predicted_tool_labels)
    true_category_labels = list(true_category_labels)
    predicted_category_labels = list(predicted_category_labels)

    # calculate union
    tool_labels_union = np.union1d(true_tool_labels, predicted_tool_labels)
    category_labels_union = np.union1d(true_category_labels, predicted_category_labels)

    # Generate confusion matrices
    tool_confusion = confusion_matrix(true_tool_labels, predicted_tool_labels, labels=tool_labels_union)
    category_confusion = confusion_matrix(true_category_labels, predicted_category_labels, labels=category_labels_union)

    # Save confusion matrices as CSV
    pd.DataFrame(tool_confusion, index=tool_labels_union, columns=tool_labels_union).to_csv(
        os.path.join(output_dir, "tool_confusion_matrix.csv")
    )
    pd.DataFrame(category_confusion, index=category_labels_union, columns=category_labels_union).to_csv(
        os.path.join(output_dir, "category_confusion_matrix.csv")
    )

    # Append accuracy information to CSV
    with open(os.path.join(output_dir, "tool_confusion_matrix.csv"), "a") as f:
        f.write("\nTool Selection Accuracy: {:.2f}%\n".format(tool_accuracy))

    with open(os.path.join(output_dir, "category_confusion_matrix.csv"), "a") as f:
        f.write("\nCategory Selection Accuracy: {:.2f}%\n".format(category_accuracy))

    # Plot and save confusion matrices as images
    plot_confusion_matrix(
        tool_confusion, tool_labels_union, 
        title=f"Tool Confusion Matrix - {input_file_name_with_count}",
        accuracy=tool_accuracy, 
        output_path=os.path.join(output_dir, "tool_confusion_matrix.jpg")
    )
    plot_confusion_matrix(
        category_confusion, category_labels_union, 
        title=f"Category Confusion Matrix - {input_file_name_with_count}",
        accuracy=category_accuracy, 
        output_path=os.path.join(output_dir, "category_confusion_matrix.jpg")
    )

    data_to_write = {
        "true_tool_name": true_tool_name,
        "true_category_name": true_category_name,
        "total_queries": total,
        "tool_accuracy": tool_accuracy,
        "category_accuracy": category_accuracy
    }
    df = pd.DataFrame([data_to_write])
    all_output_csv_path = os.path.join(os.path.dirname(output_dir), "all_accuracy.csv")
    df.to_csv(all_output_csv_path, header=not os.path.exists(all_output_csv_path), mode='a', index=False)
    


def main(args):
    if args.public:
        config = cfg_inference_public
    else:
        config = cfg_inference_local

    if config.data_dir:
        globalvar.huggingface_root = Path(config.data_dir.huggingface_root)
        globalvar.bin_root = Path(config.data_dir.bin_root)
        globalvar.modelhub_root = Path(config.data_dir.modelhub_root)
        globalvar.dataset_root = Path(config.data_dir.dataset_root)
    else:
        # Set to local folder by default
        globalvar.huggingface_root = Path("huggingface")
        globalvar.bin_root = Path("bin")
        globalvar.modelhub_root = Path("modelhub")
        globalvar.dataset_root = Path("dataset")

    if config.setting.seed:
        print("Setting up random seed")
        setup_seed(config.setting.seed)

    # Set OS environment variables
    print("Setting up OS environment variables")
    for k, v in config.setting.os_environ.items():
        if v is not None and k not in os.environ:
            os.environ[k] = str(v)
        elif k in os.environ:
            # Override the OS environment variables
            config.setting.os_environ[k] = os.environ[k]

    # Only the root node will print the log
    if config.setting.os_environ.NODE_RANK != 0:
        config.Trainer.logger = False

    # Update config data input and output
    if args.input is None:
        # make_input_file(load_toolset(config.toolset))
        args.input = "examples/inputs/all_input.json"
    # else:
    #     config.data.input = args.input
    config.data.input = args.input

    if args.output is None:
        # output_json path.
        input_file_name_without_extension = os.path.splitext(os.path.basename(args.input))[0]
        args.output = os.path.join(f"outputs/retriever_result/{input_file_name_without_extension}", f"{input_file_name_without_extension}_result.json")
        
    config.data.output = args.output


    run(config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=bool, default=True)
    parser.add_argument("--input", type=str, default=None)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()
    main(args)



