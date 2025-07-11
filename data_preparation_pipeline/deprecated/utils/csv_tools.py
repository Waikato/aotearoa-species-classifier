import csv


def load_csv_file(file_path, delimiter=','):
    data_list = []
    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        csvreader = csv.DictReader(csvfile, delimiter=delimiter)
        for row in csvreader:
            data_list.append(row)
    return data_list


def save_as_csv(data_list, file_path):
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = data_list[0].keys()
        csvwriter = csv.DictWriter(csvfile, fieldnames=fieldnames)

        csvwriter.writeheader()  # Write the header row

        for item in data_list:
            csvwriter.writerow(item)

