# =========================================================================
# -- Development Dockerfile --
# මෙම ගොනුව docker-compose සමඟ local development සඳහා පමණක් භාවිතා වේ.
# =========================================================================
FROM node:20-alpine

# වැඩ කරන directory එක සකස් කිරීම
WORKDIR /app

# package.json සහ package-lock.json ගොනු පිටපත් කිරීම
# node_modules cache එක ಉತ್ತಮ කිරීම සඳහා මෙය මුලින්ම සිදු කරයි
COPY package*.json ./

# devDependencies ඇතුළුව සියලුම dependencies ස්ථාපනය කිරීම
# development server එකට 'next' command එක අවශ්‍ය නිසා මෙය අත්‍යවශ්‍ය වේ
RUN npm install

# ඉතිරි source code එක පිටපත් කිරීම
COPY . .

# Next.js dev server එක සඳහා port 3000 නිරාවරණය කිරීම
EXPOSE 3000

# development server එක ආරම්භ කරන default command එක
CMD ["npm", "run", "dev"]
