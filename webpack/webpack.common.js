const BundleTracker = require('webpack-bundle-tracker');
const ExtractTranslationKeysPlugin = require('webpack-extract-translation-keys-plugin');
const ESLintPlugin = require('eslint-webpack-plugin');
const lodash = require('lodash');
const path = require('path');
const webpack = require('webpack');

// HACK: we needed to define this postcss-loader because of a problem with
// including CSS files from node_modules directory, i.e. this build error:
// `Error: No PostCSS Config found in: /srv/node_modules/…`
const postCssLoader = {
  loader: 'postcss-loader',
  options: {
    sourceMap: true,
    postcssOptions: {
      plugins: [
        'autoprefixer',
      ],
    },
  },
};

const babelLoader = {
  loader: 'babel-loader',
  options: {
    presets: ['@babel/preset-env', '@babel/preset-react'],
    plugins: ['react-hot-loader/babel'],
  },
};

const commonOptions = {
  module: {
    rules: [
      {
        enforce: 'pre',
        test: /\.coffee$/,
        exclude: /node_modules/,
        loader: 'less-terrible-coffeelint-loader',
        options: {
          failOnErrors: true,
          failOnWarns: false,
          // custom reporter function that only returns errors (no warnings)
          reporter: function (errors) {
            errors.forEach((error) => {
              if (error.level === 'error') {
                this.emitError([
                  error.lineNumber,
                  error.message,
                ].join(' ') + '\n');
              }
            });
          },
        },
      },
      {
        test: /\.(js|jsx|es6)$/,
        exclude: /node_modules/,
        use: babelLoader,
      },
      {
        test: /\.(ts|tsx)$/,
        exclude: /node_modules/,
        use: [
          babelLoader,
          {
            loader: 'ts-loader',
          },
        ],
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader', postCssLoader],
      },
      {
        test: /\.scss$/,
        use: ['style-loader', 'css-loader', postCssLoader, 'sass-loader'],
      },
      {
        test: /\.coffee$/,
        use: {
          loader: 'coffee-loader',
        },
      },
      {
        test: /\.(png|jpg|gif|ttf|eot|svg|woff(2)?)$/,
        type: 'asset/resource',
        generator: {
          filename: '[name].[ext]',
        },
      },
    ],
  },
  resolve: {
    extensions: ['.jsx', '.js', '.es6', '.coffee', '.ts', '.tsx'],
    alias: {
      app: path.join(__dirname, '../app'),
      jsapp: path.join(__dirname, '../jsapp'),
      js: path.join(__dirname, '../jsapp/js'),
      scss: path.join(__dirname, '../jsapp/scss'),
      utils: path.join(__dirname, '../jsapp/js/utils'),
      test: path.join(__dirname, '../test'),
    },
  },
  plugins: [
    new BundleTracker({path: __dirname, filename: 'webpack-stats.json'}),
    new ExtractTranslationKeysPlugin({
      functionName: 't',
      output: path.join(__dirname, '../jsapp/compiled/extracted-strings.json'),
    }),
    new webpack.ProvidePlugin({'$': 'jquery'}),
    new ESLintPlugin({
      quiet: true,
      extensions: ['js', 'jsx', 'ts', 'tsx', 'es6'],
    }),
  ],
};

module.exports = function (options) {
  options = lodash.mergeWith(
    commonOptions, options || {},
    (objValue, srcValue) => {
      if (lodash.isArray(objValue)) {
        return objValue.concat(srcValue);
    }
  });
  return options;
};
