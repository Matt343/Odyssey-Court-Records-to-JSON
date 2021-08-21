import os
import requests
from time import sleep

from bs4 import BeautifulSoup

import scrape_calendar_data

MS_WAIT_PER_REQUEST = 200

main_page_url = "http://public.co.hays.tx.us/"
calendar_page_url = "http://public.co.hays.tx.us/Search.aspx?ID=900&NodeID=100,101,102,103,200,201,202,203,204,6112,400,401,402,403,404,405,406,407,6111,6114&NodeDesc=All%20Courts"

judicial_officer_to_ID = {
    "visiting_officer": "37809",
    "Boyer_Bruce": "39607",
    "Johnson_Chris": "48277",
    "Robison_Jack": "6140",
    "Sherri_Tibbe": "55054",
    "Henry_Bill": "25322",
    "Steel_Gary": "6142",
    "Updegrove_Robert": "38628",
    "Zelhart_Tacie": "48274",
}


if __name__ == "__main__":
    # Initial setup for the session
    session = requests.Session()
    main_page = session.get(main_page_url)

    # May not be necessary, grabbing viewstate for form data
    calendar_page = session.get(calendar_page_url)
    soup = BeautifulSoup(calendar_page.text, "html.parser")
    viewstate_token = soup.find(id="__VIEWSTATE")["value"]

    # Data dir setup - added this to gitignore for now, may want to remove later
    if not os.path.exists("data_by_JO"):
        os.mkdir("data_by_JO")
    for JO_name, JO_id in judicial_officer_to_ID.items():
        print(f"Processing {JO_name}")
        # Make folders if they don't exist
        JO_path = os.path.join("data_by_JO", JO_name)
        JO_case_path = os.path.join(JO_path, "case_html")
        JO_cal_path = os.path.join(JO_path, "calendar_html")
        if not os.path.exists(JO_path):
            os.mkdir(JO_path)
        if not os.path.exists(JO_case_path):
            os.mkdir(JO_case_path)
        if not os.path.exists(JO_cal_path):
            os.mkdir(JO_cal_path)

        for cal_html_file in os.scandir(JO_cal_path):
            if not cal_html_file.is_dir():
                case_date = cal_html_file.name.split(".")[0]
                print(f"Processing cases from {case_date} for {JO_name}")
                with open(cal_html_file.path, "r") as file_handle:
                    cal_html_str = file_handle.read()
                cal_soup = BeautifulSoup(cal_html_str, "html.parser")
                case_anchors = cal_soup.select('a[href^="CaseDetail"]')
                if case_anchors:
                    # Continue with the next cal html file is all cases are cached
                    if all(
                        os.path.exists(
                            os.path.join(
                                JO_case_path,
                                f"{case_date} {case_anchor['href'].split('=')[1]}.html",
                            )
                        )
                        for case_anchor in case_anchors
                    ):
                        print("All cases are cached for this file.")
                        continue

                    session.post(
                        calendar_page_url,
                        data=scrape_calendar_data.make_form_data(
                            case_date, JO_id, viewstate_token
                        ),
                    )
                for case_anchor in case_anchors:
                    case_url = main_page_url + case_anchor["href"]
                    case_id = case_url.split("=")[1]
                    case_html_file_path = os.path.join(
                        JO_case_path, f"{case_date} {case_id}.html"
                    )

                    if not os.path.exists(case_html_file_path):
                        # Make request for the case
                        print("Visiting", case_url)
                        # TODO: need to visit case calendar page before case url during session
                        case_results = session.get(case_url)
                        # Error check based on text in html result.
                        if "Date Filed" in case_results.text:
                            print(f"Writing file: {case_html_file_path}")
                            with open(case_html_file_path, "w") as file_handle:
                                file_handle.write(case_results.text)
                            # Rate limiting - convert ms to seconds
                            sleep(MS_WAIT_PER_REQUEST / 1000)
                        else:
                            print(
                                f'ERROR: "Date Filed" substring not found in case html page. Aborting. Writing ./debug.html'
                            )
                            with open("debug.html", "w") as file_handle:
                                file_handle.write(case_results.text)
                            quit()
                        # Rate limiting - convert ms to seconds
                        sleep(MS_WAIT_PER_REQUEST / 1000)
                    else:
                        print("Data is already cached. Skipping.")
