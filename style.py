for files in file_types:
    try:
        file_exists = exists('.google-cookie')
        if file_exists == True:
            os.remove('.google-cookie')
        rand_user = random.choice(user_agents)
        rand_ipv4 = random.choice(address)
        rand_ipv6 = random.choice(ip6)
        print(f"\033[1;33m[>] Processing <\b> Searching Info For {files}")

        for results in search(f'site:{target} filetype:{files}', num_results=3):
            print(results)
            wget.download(results, out=target)
            req = 1

    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(fail + f" [404] Download Fail, Skipping")
            continue
        if e.code == 403:
            print(fail + f" [403] Download Fail, Skipping")
            continue
