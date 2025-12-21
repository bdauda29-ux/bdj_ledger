# How to Get the Android APK

Since building an Android app requires heavy tools (Android Studio, JDK, SDK) that are not installed in this environment, I have set up an **Automated Build Pipeline on GitHub**.

### Steps to Download Your APK:

1.  **Push your code** to GitHub (already done).
2.  Go to your repository on GitHub: `https://github.com/bdauda29-ux/bdj_ledger`
3.  Click on the **"Actions"** tab at the top.
4.  On the left sidebar, click on **"Build Android APK"**.
5.  Click the **"Run workflow"** button on the right.
    *   **App URL**: Enter the live URL where your website is hosted (e.g., `https://your-app.onrender.com` or `https://bdj-ledger.vercel.app`).
    *   *Note: An APK needs a live website to display content. It cannot connect to "localhost" on your computer.*
6.  Click **"Run workflow"** (green button).
7.  Wait for the build to finish (about 2-5 minutes).
8.  Click on the completed run title.
9.  Scroll down to the **"Artifacts"** section.
10. Click on **"BDJ-Ledger-APK"** to download the `.zip` file containing your APK.

### Installing on Phone:
1.  Transfer the downloaded APK to your Android phone.
2.  Open it and tap **Install**.
3.  You might need to allow "Install from unknown sources" since this is a self-signed app.

### Why this approach?
This method uses GitHub's powerful cloud servers to compile the Android app, saving you from installing gigabytes of Android development tools on your local machine.
